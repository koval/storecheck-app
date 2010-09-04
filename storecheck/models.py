# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User

class Address(models.Model):
    city = models.CharField(u'місто', max_length=50)
    district = models.CharField(u'район', max_length=50)
    street = models.CharField(u'вулиця', max_length=50)
    building = models.CharField(u'будинок', max_length=50)

    def __unicode__(self):
        title = u'%s, %s р-н, вул. %s, %s' % (self.city, self.district, 
            self.street, self.building)
        return title 

class Store(models.Model):
    address = models.ForeignKey(Address, verbose_name=u'фактична адреса', related_name='store_set')
    legal_address = models.ForeignKey(Address, verbose_name=u'юридична адреса', related_name='legal_store_set')
    name = models.CharField(u'назва', max_length=50)
    branding = models.BooleanField(u'брендування') # or NullBooleanField do have an 'Undefined' value

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('team12.storecheck.views.check', [str(self.id)])

class Refrigerator(models.Model):
    store = models.ForeignKey(Store, verbose_name=u'торгова точка')
    serial_number = models.CharField(u'серійний номер', max_length=50)
    baskets = models.PositiveIntegerField(u'кількість корзин')
    filled = models.BooleanField(u'викладка')
    fill_percentage = models.PositiveIntegerField(u'відсоток наповнення')
    branding = models.BooleanField(u'брендування')
    original_price_list = models.BooleanField(u'фірмовий цінник')
    serial_number_sticker = models.BooleanField(u'наклейка із серійним номером')
    glass_number = models.PositiveIntegerField(u'кількість скла')

    def __unicode__(self):
        return unicode(self.serial_number)

class StoreAssignment(models.Model):
    store = models.OneToOneField(Store, primary_key=True, verbose_name=u'торгова точка')
    user = models.ForeignKey(User, verbose_name=u'регіональний менеджер')
    checked = models.BooleanField(u'перевірена')

    def save(self, *args, **kwargs):
        for ref in self.store.refrigerator_set.all():
            try:
                RefrigeratorAssignment.objects.get(refrigerator=ref)
            except RefrigeratorAssignment.DoesNotExist, e:
                # create the assignment for a refrigerator
                a = RefrigeratorAssignment(refrigerator=ref, user=self.user)
                a.save()

        # Call the "real" save() method.
        super(StoreAssignment, self).save(*args, **kwargs)

    def __setattr__(self, name, value):
        if name == "user":
            # store was reassigned update refrigerator assignments
            try:
                old_value = self.user
            except User.DoesNotExist:
                return super(StoreAssignment, self).__setattr__(name, value)
            if old_value != value:
                for ref in self.store.refrigerator_set.all():
                    try:
                        a = RefrigeratorAssignment.objects.get(refrigerator=ref)
                        a.user = value
                    except RefrigeratorAssignment.DoesNotExist, e:
                        # create the assignment for a refrigerator
                        a = RefrigeratorAssignment(refrigerator=ref, user=value)
                    a.save()
        super(StoreAssignment, self).__setattr__(name, value)

    # def delete(self, *args, **kwargs):
    #    pass

    def __unicode__(self):
        return u'%s: перевірка %s' % (self.user.username,
            self.store.name)

class RefrigeratorAssignment(models.Model):
    refrigerator = models.OneToOneField(Refrigerator, primary_key=True, verbose_name=u'морозильна камера')
    user = models.ForeignKey(User, verbose_name=u'регіональний менеджер')
    checked = models.BooleanField(u'перевірена')

    def __unicode__(self):
        return u'%s: перевірка %s' % (self.user.username,
            self.refrigerator.serial_number)
