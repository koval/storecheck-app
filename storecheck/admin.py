# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib import databrowse

from storecheck.models import Address, Store, Refrigerator, StoreAssignment, \
    RefrigeratorAssignment

class AddressAdmin(admin.ModelAdmin):
    list_display = ('city', 'district', 'street', 'building')

class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'branding')

class RefrigeratorAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'store')

class StoreAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'checked')

class RefrigeratorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'refrigerator', 'checked')

    def store(self, obj):
        return obj.refrigerator.store
    store.short_description = u'Торгова точка'
    store.admin_order_field = 'user'

# register admin forms
admin.site.register(Address, AddressAdmin)
admin.site.register(Refrigerator, RefrigeratorAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(StoreAssignment, StoreAssignmentAdmin)
admin.site.register(RefrigeratorAssignment, RefrigeratorAssignmentAdmin)

# and databrowser pages
databrowse.site.register(Address)
databrowse.site.register(Store)
databrowse.site.register(Refrigerator)
databrowse.site.register(StoreAssignment)
databrowse.site.register(RefrigeratorAssignment)
