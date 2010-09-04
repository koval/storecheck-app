# -*- coding: utf-8 -*-
import cgi
import cStringIO

from django import forms
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden, Http404, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.utils.decorators import available_attrs
from django.utils.http import urlquote

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.4 fallback.

try:
    import ho.pisa as pisa
    HAS_PDF_SUPPORT = True
except ImportError, e:
    HAS_PDF_SUPPORT = False

from storecheck.models import Store, Refrigerator, StoreAssignment, \
    RefrigeratorAssignment, Address

class BaseView(object):
    """ A base class for views that delegates handling to GET, POST methods
        based on reques method. An instance of this class must be created to be
        used in the url patterns.
    """

    def __call__(self, request, *args, **kwargs):
        method = request.method.lower()
        if hasattr(self, method):
            return getattr(self, method)(request, *args, **kwargs)
        else:
            raise Http404('Not supported HTTP method.')

# HACK: modify django.contrib.auth.decorators.login_required to support views
# that a class instances (not functions)
def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        def _wrapped_view(self, request, *args, **kwargs):
            if test_func(request.user):
                return view_func(self, request, *args, **kwargs)
            path = urlquote(request.get_full_path())
            tup = login_url, redirect_field_name, path
            return HttpResponseRedirect('%s?%s=%s' % tup)
        return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)
    return decorator

def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated(),
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

class Index(BaseView):
    """ Site main page, which has management and standard interface.
    """

    @login_required
    def get(self, request):
        if request.user.is_superuser:
            users = [u for u in User.objects.all() if not u.is_superuser]
            stores = []
            for store in Store.objects.all():
                try:
                    assignment = StoreAssignment.objects.get(store=store)
                    all = 1
                    done = assignment.checked and 1 or 0
                    # get progress of a store check
                    for ref in store.refrigerator_set.all():
                        all += 1
                        if ref.refrigeratorassignment.checked:
                            done += 1
                    progress = done * 100/all
                    stores.append((store, assignment.user.username, progress))
                except StoreAssignment.DoesNotExist:
                    stores.append((store, None, False))
            return render_to_response('storecheck/admin.html', {
                'users': users,
                'stores': stores,},
                context_instance=RequestContext(request))
        else:
            return render_to_response('storecheck/index.html', 
                context_instance=RequestContext(request))

class Addresses(BaseView):
    """ A page with store and refrigerator addresses. List of addresses can be
        filtered by store's location or refrigerator's serial number.
    """

    @login_required
    def get(self, request):
        user = request.user
        stores = []
        refrigerators = []
        # default value to make refrigerators tab active
        q = {'type': 'serial', 'search': False}
        assignments = StoreAssignment.objects.filter(user=user)
        for i in assignments:
            stores.append((i, i.store))
            for ref in i.store.refrigerator_set.all():
                try:
                    assignment = ref.refrigeratorassignment
                    refrigerators.append((assignment, ref))
                except RefrigeratorAssignment.DoesNotExist, e:
                    # for safety - skip those refrigerators that has no 
                    # assignments
                    pass

        return render_to_response('storecheck/addresses.html', {
            'stores': stores,
            'refrigerators': refrigerators,
            'query': q},
            context_instance=RequestContext(request))

    @login_required
    def post(self, request):
        user = request.user
        stores = []
        refrigerators = []
        # query items, 'type' is mandatory, because it identifies the query type to
        # make some tab active
        q = {}

        post = request.POST
        if 'serial' in post:
            q['type'] = 'serial'
            q['search'] = True
            # handle a search query by the serial number
            q['serial'] = post.getlist('serial')
            for sn in post.getlist('serial'):
                try:
                    assignment = RefrigeratorAssignment.objects.get(user=user, refrigerator__serial_number=sn)
                    refrigerators.append((assignment, assignment.refrigerator))
                except RefrigeratorAssignment.DoesNotExist, e:
                    # user has no assigned regfrigerator with given serial number
                    pass
            # get stores that contain matched refrigerators
            only_stores = []
            for a, ref in refrigerators:
                if ref.store not in only_stores:
                    only_stores.append(ref.store)

            # now make list of (store_assignment, store) pairs
            for store in only_stores:
                try:
                    assignment = store.storeassignment
                    stores.append((assignment, store))
                except StoreAssignment.DoesNotExist, e:
                    pass
        else:
            # handle a search query by the store location
            for name in ["city", "district", "street", "building"]:
                value = post.get(name)
                if value:
                    if name == 'building': value = int(value)
                    q['store__address__%s' % name] = post[name]

            assignments = StoreAssignment.objects.filter(user=user, **q)
            for i in assignments:
                stores.append((i, i.store))
                for ref in i.store.refrigerator_set.all():
                    try:
                        assignment = ref.refrigeratorassignment
                        refrigerators.append((assignment, ref))
                    except RefrigeratorAssignment.DoesNotExist, e:
                        # for safety - skip those refrigerators that has no 
                        # assignments
                        pass
            q['type'] = 'location'
            q['search'] = True

        return render_to_response('storecheck/addresses.html', {
            'stores': stores,
            'refrigerators': refrigerators,
            'query': q},
            context_instance=RequestContext(request))

class RefrigeratorEditForm(forms.ModelForm):
    fill_percentage = forms.IntegerField(min_value=0, max_value=100, 
        required=True, label=u'Відсоток наповнення')

    class Meta:
        model = Refrigerator

class StoreEditForm(forms.ModelForm):
    class Meta:
        model = Store

class Check(BaseView):
    """ Store & refrigerator view where information about them is displayed and 
        can be edited.
    """

    @login_required
    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)
        store_assignment = StoreAssignment.objects.get(store=store)
        refrigerators = []
        for ref in store.refrigerator_set.all():
            try:
                assignment = RefrigeratorAssignment.objects.get(refrigerator=ref)
                refrigerators.append((ref.serial_number, assignment,
                    RefrigeratorEditForm(instance=ref, label_suffix='')))
            except RefrigeratorAssignment.DoesNotExist:
                pass
        store_form = StoreEditForm(instance=store, label_suffix='')

        # determine the active tab
        try:
            reftab = refrigerators[0][0]
        except IndexError:
            reftab = None
        storetab = False
        if 'sn' in request.GET:
            reftab = request.GET['sn']
        else:
            storetab = True

        return render_to_response('storecheck/check.html', {
            'store': store,
            'store_assignment': store_assignment,
            'store_form': store_form,
            'refrigerators': refrigerators,
            'reftab': reftab,
            'storetab': storetab},
            context_instance=RequestContext(request))

    @login_required
    def post(self, request, store_id):
        if 'refrigerator_pk' in request.POST:
            # editing refrigerator information
            ref = Refrigerator.objects.get(pk=request.POST['refrigerator_pk'])
            form = RefrigeratorEditForm(request.POST, instance=ref)
        else:
            # editing store information
            store = Store.objects.get(pk=store_id)
            form = StoreEditForm(request.POST, instance=store)
        if form.is_valid(): # All validation rules pass
            form.save()
            if 'refrigerator_pk' in request.POST:
                assignment = RefrigeratorAssignment.objects.get(refrigerator=ref)
                assignment.checked = True
                assignment.save()
            else:
                assignment = StoreAssignment.objects.get(store=store)
                assignment.checked = True
                assignment.save()
            return HttpResponse(request.build_absolute_uri('/addresses'))
        else:
            return HttpResponse(form.as_table())

class AddressAutocomplete(BaseView):
    """ Autocomple supporting view for the address fields (for list of fields
        see Address model).
    """

    @login_required
    def get(self, request):
        data = dict(request.GET)
        # get name of a currently active field
        field = str(data.pop('field')[0])
        # remove unused parameters
        data.pop('q')
        data.pop('timestamp')
        # get limit (currently unused(
        limit = int(data.pop('limit')[0])
        # get value of the currently active field
        q = data.pop(field)[0]
        query = {'%s__contains' % field: q}

        # add rest of data to the query
        for k, v in data.items():
            value = v[0]
            if value:
                query['%s' % str(k)] = v[0]

        # now query database
        results = []
        for r in Address.objects.filter(**query).values_list(field):
            results.append(r[0])
        # get only unique values
        results = list(set(results))[:limit]

        return HttpResponse('\n'.join(results))

class SerialNumberAutocomplete(BaseView):
    """ Autocomplete support view for the 'serial_number' field of the 
        Refrigerator model.
    """

    @login_required
    def get(self, request):
        """ Autocomple support for serial number fields.
        """
        data = dict(request.GET)

        # get already selected values
        selected = data.get('serials')

        # remove unused parameters
        q = data.pop('q')[0]

        # get limit (currently unused(
        limit = int(data.pop('limit')[0])

        if request.user.is_authenticated():
            query = {'refrigerator__serial_number__contains': q, 'user': request.user}
        else:
            query = {'refrigerator__serial_number__contains': q}

        # now query database
        results = []
        for r in RefrigeratorAssignment.objects.filter(**query).values_list('refrigerator__serial_number'):
            if r[0] not in selected:
                results.append(r[0])
        # get only unique values
        results = list(set(results))[:limit]

        return HttpResponse('\n'.join(results))

class Assign(BaseView):
    """ A view to handle (re)assigning store checks. Can be used only by 
        superuser.
    """

    @login_required
    def get(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        for key, value in request.GET.items():
            # handle some action (reassing, reset store assignment)
            if key.startswith('store'):
                # reassing store
                store_pk = key.replace('store', '')
                user_pk = value.replace('user', '')
                # check for existance of the store
                try:
                    store = Store.objects.get(pk=store_pk)
                except Store.DoesNotExist:
                    continue

                # check for existance of the user
                try:
                    user = User.objects.get(pk=user_pk)
                except User.DoesNotExist:
                    continue

                assignment = StoreAssignment.objects.filter(store=store)
                if assignment:
                    # change existing assignment
                    assignment = assignment[0]
                    assignment.user = user
                    assignment.save()
                else:
                    assignment = StoreAssignment()
                    assignment.user = user
                    assignment.store = store
                    assignment.save()
            elif key == 'reset':
                for value in request.GET.getlist(key):
                    # reset store assignment status
                    store_pk = value.replace('store', '')
                    try:
                        store = Store.objects.get(pk=store_pk)
                    except Store.DoesNotExist:
                        continue
                    try:
                        assignment = StoreAssignment.objects.get(store=store)
                    except StoreAssignment.DoesNotExists:
                        continue
                    assignment.checked = False
                    assignment.save()
                    # reset also refrigerator assignments (should this be moved to the model?)
                    for ref in store.refrigerator_set.filter(refrigeratorassignment__checked=True):
                        ref.refrigeratorassignment.checked = False
                        ref.refrigeratorassignment.save()

        return HttpResponseRedirect('/')

class Report(BaseView):
    """ A view to generate store check reports in the PDF format. This view uses
        a pisa package, which requires:
         * reportlab (to build it next packages must be installed: python-dev, 
           build-essential, libfreetype6 and libfreetype6-dev)
         * html5lib
         * PIL
    """

    @login_required
    def get(self, request):
        """ Generate reports for chosen store checks.
        """
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        # get preferred format from the request (defaults to pdf)
        format = request.GET.get('format', 'pdf')

        stores = []
        for value in request.GET.getlist('report'):
            # handle some action (reassing, reset store assignment)
            store_pk = value.replace('store', '')
            try:
                store = Store.objects.get(pk=store_pk)
            except Store.DoesNotExist:
                continue
            refs = store.refrigerator_set.filter(refrigeratorassignment__checked=True)
            stores.append((store, refs))

        if format == 'pdf':
            return self.writePdf('storecheck/report.html',{
                'pagesize' : 'A4',
                'stores' : stores})
        elif format == 'html':
            return render_to_response('storecheck/report.html', {
                'stores': stores})
        else:
            return HttpResponseBadRequest('Not supported report format: %s' % format)

    def writePdf(self, template_src, context_dict):
        """ Generate PDF file from rendered template.
             * template_src - path to django template;
             * context_dict - template context dictionary.
        """
        if not HAS_PDF_SUPPORT:
            return HttpResponse('PDF export for reports isn\'t supported! '
                'Install a "ho.pisa" library')
        template = get_template(template_src)
        context = Context(context_dict)
        html  = template.render(context)
        result = cStringIO.StringIO()
        pdf = pisa.pisaDocument(cStringIO.StringIO(
            html.encode("utf-8")), result, encoding='utf-8')
        if not pdf.err:
            response = HttpResponse(mimetype='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=storecheck.pdf'
            response.write(result.getvalue())
            return response
        return HttpResponse('Gremlin\'s ate your pdf! %s' % cgi.escape(html))

# instantiate all view classes
index = Index()
check = Check()
addresses = Addresses()
sn_autocomplete = SerialNumberAutocomplete()
address_autocomplete = AddressAutocomplete()
assign = Assign()
report = Report()

class MobileIndex(BaseView):
    """ Mobile index page optimized for Mobile Safari.
    """
    def get(self, request):
        return render_to_response('storecheck/mobile/index.html', 
            context_instance=RequestContext(request))

mobile_index = MobileIndex()

class MobileAddresses(BaseView):
    """ Mobile addresses page optimized for Mobile Safari.
    """

    def get(self, request):
        stores = []
        refrigerators = []
        # query items, 'type' is mandatory, because it identifies the query type to
        # make some tab active
        q = {}

        post = request.GET
        if 'serial' in post:
            q['type'] = 'serial'
            q['search'] = True
            # handle a search query by the serial number
            q['serial'] = post.getlist('serial')
            for sn in post.getlist('serial'):
                try:
                    assignment = RefrigeratorAssignment.objects.get(refrigerator__serial_number=sn)
                    refrigerators.append((assignment, assignment.refrigerator))
                except RefrigeratorAssignment.DoesNotExist, e:
                    # user has no assigned regfrigerator with given serial number
                    pass
            # get stores that contain matched refrigerators
            only_stores = []
            for a, ref in refrigerators:
                if ref.store not in only_stores:
                    only_stores.append(ref.store)

            # now make list of (store_assignment, store) pairs
            for store in only_stores:
                try:
                    assignment = store.storeassignment
                    stores.append((assignment, store))
                except StoreAssignment.DoesNotExist, e:
                    pass
        else:
            # handle a search query by the store location
            for name in ["city", "district", "street", "building"]:
                value = post.get(name)
                if value:
                    if name == 'building': value = int(value)
                    q['store__address__%s' % name] = post[name]

            assignments = StoreAssignment.objects.filter(**q)
            for i in assignments:
                stores.append((i, i.store))
                for ref in i.store.refrigerator_set.all():
                    try:
                        assignment = ref.refrigeratorassignment
                        refrigerators.append((assignment, ref))
                    except RefrigeratorAssignment.DoesNotExist, e:
                        # for safety - skip those refrigerators that has no 
                        # assignments
                        pass
            q['type'] = 'location'
            q['search'] = True

        return render_to_response('storecheck/mobile/addresses.html', {
            'stores': stores,
            'refrigerators': refrigerators,
            'query': q},
            context_instance=RequestContext(request))

mobile_addresses = MobileAddresses()

class MobileCheck(BaseView):
    """ Store & refrigerator view where information about them is displayed and 
        can be edited (optimized for Mobile Safari).
    """

    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)
        store_assignment = StoreAssignment.objects.get(store=store)
        refrigerators = []
        for ref in store.refrigerator_set.all():
            try:
                assignment = RefrigeratorAssignment.objects.get(refrigerator=ref)
                refrigerators.append((ref.serial_number, assignment,
                    RefrigeratorEditForm(instance=ref, label_suffix='')))
            except RefrigeratorAssignment.DoesNotExist:
                pass
        store_form = StoreEditForm(instance=store, label_suffix='')

        return render_to_response('storecheck/mobile/check.html', {
            'store': store,
            'store_assignment': store_assignment,
            'store_form': store_form,
            'refrigerators': refrigerators},
            context_instance=RequestContext(request))

mobile_check = MobileCheck()
