from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

import os

from django.contrib import databrowse

urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
    (r'^favicon.ico$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'static'), 'path': 'favicon.ico'}),
    (r'^$', 'storecheck.views.index'),
    (r'^addresses$', 'storecheck.views.addresses'),
    (r'^check/(?P<store_id>\d+)/$', 'storecheck.views.check'),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),
    (r'^autocomplete/address$', 'storecheck.views.address_autocomplete'),
    (r'^autocomplete/sn$', 'storecheck.views.sn_autocomplete'),
    (r'^assign$', 'storecheck.views.assign'),
    (r'^report$', 'storecheck.views.report'),
    (r'^m/$', 'storecheck.views.mobile_index'),
    (r'^m/addresses$', 'storecheck.views.mobile_addresses'),
    (r'^m/check/(?P<store_id>\d+)/$', 'storecheck.views.mobile_check'),

    # some django standard apps
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^databrowse/(.*)', databrowse.site.root),
)
