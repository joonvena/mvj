import datetime

from django import forms
from django.db.models import Avg, Count, Q, Sum
from django.utils.translation import ugettext_lazy as _
from rest_framework.response import Response

from leasing.enums import LeaseAreaAttachmentType, LeaseState, RentType, SubventionType, TenantContactType
from leasing.models import Lease
from leasing.report.report_base import ReportBase


def get_type(obj):
    if not obj.state:
        return
    return obj.state.value


def get_lease_id(obj):
    return obj.get_identifier_string()


class LeaseListsReport(ReportBase):
    name = _("Lease Lists")
    description = _("Lease lists")
    slug = "lease_lists"
    input_fields = {
        "start_date": forms.DateField(label=_("Start date"), required=True),
        "end_date": forms.DateField(label=_("End date"), required=True),
    }
    output_fields = {
        "lease_id": {"label": _("Lease id"), "source": get_lease_id},
        "start_date": {"label": _("Start date")},
        "end_date": {"label": _("End date")},
    }
    automatic_excel_column_labels = False

    def get_data(self, input_data):
        qs = (
            Lease.objects.filter(
                (
                    Q(start_date__gte=input_data["start_date"])
                    & Q(start_date__lte=input_data["end_date"])
                )
                | (
                    Q(end_date__gte=input_data["start_date"])
                    & Q(end_date__lte=input_data["end_date"])
                )
            )
        ).prefetch_related(
            'lease_areas',
            'tenants',
            'tenants__tenantcontact_set',
            'tenants__tenantcontact_set__contact',
        )

        return qs

    # 1.1 Vuokraukset, joissa ei ole laskutus käynnissä
    def get_invoicing_not_enabled(self, report_data):
        return self.serialize_data(report_data.filter(is_invoicing_enabled=False))

    # 1.2 Vuokraukset, joissa ei ole vuokratiedot kunnossa
    def get_rent_info_not_complete(self, report_data):
        return self.serialize_data(report_data.filter(is_rent_info_complete=False))

    # 1.3 Vuokraukset, joissa ei ole vuokratietoja
    def get_no_rents(self, report_data):
        return self.serialize_data(report_data.annotate(rent_count=Count('rents')).filter(rent_count=0))

    # 1.4 Vuokraukset, joissa ei ole eräpäivää (Vuokraukset, joissa vuokralaji on valittu, mutta ei ole eräpäivää)
    def get_no_due_date(self, report_data):
        ret = []
        for lease in report_data.all():
            due_dates = False
            for rent in lease.rents.exclude(type__isnull=True):
                if(rent.due_dates.count() > 0):
                    due_dates = True
            if(not due_dates):
                ret.append({'lease_id': lease.get_identifier_string()})
        return ret

    # 1.5 Vuokraukset, joilla on kertakaikkinen vuokra mutta ei ole laskuja.
    def get_one_time_rents_with_no_invoice(self, report_data):
        ret = []
        for lease in report_data.all():
            for rent in lease.rents.all():
                if(rent.type == RentType.ONE_TIME and lease.invoices.count() == 0):
                    ret.append({'lease_id': lease.get_identifier_string()})
        return ret

    # 1.6 Vuokraukset, joissa on virheellinen hallintaosuus
    def get_incorrect_rent_shares(self, report_data, start_date, end_date):
        ret = []
        # TODO: start_date, end_date periods?
        for lease in report_data.all():
            sum = 0
            for tenant in lease.tenants.all():
                print(tenant.share_denominator)
                sum = sum + tenant.share_numerator / tenant.share_denominator
            if(sum > 1):
                ret.append({'lease_id': lease.get_identifier_string(), 'sum': sum})

#                shares = tenant.rent_shares.all()
#                for share in shares:
#                    print(share.intended_use)
#                    print(share.share_numerator)
#                    print(share.share_denominator)
                #tenantcontacts = tenant.tenantcontact_set.filter(range_filter).order_by('-start_date')
                #for contact in tenantcontacts.all():
                #    print(contact)

#                tenant.get_tenantcontacts_for_period(start_date, end_date)
#                print(tenant.start_date)
#  items.forEach((item) => {
#    dateRangesWithItems.forEach((range) => {
#      if(isDateRangesCollapsing({
#        start_date: get(item, startDatePath),
#        end_date: get(item, endDatePath),
#      }, range)) {
#        range.items.push(item);
#      }
#    });
#  });

        return ret

    # 1.7 Vuokraukset, joissa on virheellinen laskutusosuus
    def get_incorrect_invoice_shares(self, report_data, start_date, end_date):
        ret = []
        # TODO: start_date, end_date periods?
        for lease in report_data.all():
            sum = 0
            for tenant in lease.tenants.all():
                print(tenant.share_denominator)
                sum = sum + tenant.share_numerator / tenant.share_denominator
            if(sum > 1):
                ret.append({'lease_id': lease.get_identifier_string(), 'sum': sum})

    # 1.8 Vuokraukset, joissa ei ole voimassaolevaa vuokraajaa
    def get_no_tenant_contact(self, report_data, start_date, end_date):
        ret = []
        # TODO: start_date, end_date periods?
        for lease in report_data.all():
            print(lease.get_identifier_string())
            for tenant in lease.tenants.all():
                valid_tenant = False
                if (not valid_tenant):
                    for tc in tenant.tenantcontact_set.all():
                        if tc.type != TenantContactType.TENANT:
                            continue
                        if (tc.end_date is None or tc.end_date >= end_date) and \
                                (tc.start_date is None or tc.start_date <= end_date):
                            valid_tenant = True
                        else:
                            print(tc)
                else:
                    ret.append({'lease_id': lease.get_identifier_string()})

        return ret

    # 1.9 Vuokraukset, joissa ei ole vuokrakohdetta
    def get_no_lease_area(self, report_data):
        ret = report_data.annotate(lease_area_count=Count('lease_areas')).filter(lease_area_count=0)
        return self.serialize_data(ret)


    def get_response(self, request):
        input_data = self.get_input_data(request)
        report_data = self.get_data(input_data)
        #invoicing_not_enabled = self.get_invoicing_not_enabled(report_data)
        #rent_info_not_complete = self.get_rent_info_not_complete(report_data)
        #no_rents = self.get_no_rents(report_data)
        no_due_date = self.get_no_due_date(report_data)
        #one_time_rents_with_no_invoice = self.get_one_time_rents_with_no_invoice(report_data)
        #incorrect_rent_shares = self.get_incorrect_rent_shares(report_data, input_data["start_date"], input_data["end_date"])
        #incorrect_invoice_shares = self.get_incorrect_invoice_shares(report_data, input_data["start_date"], input_data["end_date"])
        #no_tenant_contact = self.get_no_tenant_contact(report_data, input_data["start_date"], input_data["end_date"])
        #no_lease_area = self.get_no_lease_area(report_data)

        aggregated_data = [
            {
                #'invoicing_not_enabled': invoicing_not_enabled,
                #'rent_info_not_complete': rent_info_not_complete,
                #'no_rents': no_rents,
                'no_due_date': no_due_date,
                #'one_time_rents_with_no_invoice': one_time_rents_with_no_invoice,
                #'incorrect_rent_shares': incorrect_rent_shares,
                #'incorrect_invoice_shares': incorrect_invoice_shares,
                #'no_tenant_contact': no_tenant_contact,
                #'no_lease_area': no_lease_area,
            }
        ]

        return Response(aggregated_data)
