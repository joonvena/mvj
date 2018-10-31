import rest_framework.urls
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework import routers
from rest_framework_swagger.views import get_swagger_view

from leasing.views import ktj_proxy
from leasing.viewsets.area_note import AreaNoteViewSet
from leasing.viewsets.basis_of_rent import BasisOfRentViewSet
from leasing.viewsets.comment import CommentTopicViewSet, CommentViewSet
from leasing.viewsets.contact import ContactViewSet
from leasing.viewsets.debt_collection import (
    CollectionCourtDecisionViewSet, CollectionLetterTemplateViewSet, CollectionLetterViewSet, CollectionNoteViewSet)
from leasing.viewsets.decision import DecisionViewSet
from leasing.viewsets.infill_development_compensation import (
    InfillDevelopmentCompensationAttachmentViewSet, InfillDevelopmentCompensationViewSet)
from leasing.viewsets.invoice import InvoiceRowViewSet, InvoiceSetViewSet, InvoiceViewSet
from leasing.viewsets.lease import (
    DistrictViewSet, FinancingViewSet, HitasViewSet, IntendedUseViewSet, LeaseTypeViewSet, LeaseViewSet,
    ManagementViewSet, MunicipalityViewSet, NoticePeriodViewSet, RegulationViewSet, RelatedLeaseViewSet,
    StatisticalUseViewSet, SupportiveHousingViewSet)
from leasing.viewsets.rent import IndexViewSet
from leasing.viewsets.vat import VatViewSet
from users.viewsets import UserViewSet

router = routers.DefaultRouter()
router.register(r'area_note', AreaNoteViewSet)
router.register(r'basis_of_rent', BasisOfRentViewSet)
router.register(r'collection_court_decision', CollectionCourtDecisionViewSet)
router.register(r'collection_letter', CollectionLetterViewSet)
router.register(r'collection_letter_template', CollectionLetterTemplateViewSet)
router.register(r'collection_note', CollectionNoteViewSet)
router.register(r'comment', CommentViewSet)
router.register(r'comment_topic', CommentTopicViewSet)
router.register(r'contact', ContactViewSet)
router.register(r'decision', DecisionViewSet)
router.register(r'district', DistrictViewSet)
router.register(r'financing', FinancingViewSet)
router.register(r'hitas', HitasViewSet)
router.register(r'index', IndexViewSet)
router.register(r'infill_development_compensation', InfillDevelopmentCompensationViewSet)
router.register(r'infill_development_compensation_attachment', InfillDevelopmentCompensationAttachmentViewSet)
router.register(r'invoice', InvoiceViewSet)
router.register(r'invoice_row', InvoiceRowViewSet)
router.register(r'invoice_set', InvoiceSetViewSet)
router.register(r'intended_use', IntendedUseViewSet)
router.register(r'lease', LeaseViewSet, base_name='lease')
router.register(r'lease_type', LeaseTypeViewSet)
router.register(r'management', ManagementViewSet)
router.register(r'municipality', MunicipalityViewSet)
router.register(r'notice_period', NoticePeriodViewSet)
router.register(r'regulation', RegulationViewSet)
router.register(r'related_lease', RelatedLeaseViewSet)
router.register(r'statistical_use', StatisticalUseViewSet)
router.register(r'supportive_housing', SupportiveHousingViewSet)
router.register(r'user', UserViewSet)
router.register(r'vat', VatViewSet)

urlpatterns = [
    path('v1/', include(router.urls)),
    re_path(r'(?P<base_type>ktjki[ir])/tuloste/(?P<print_type>[\w/]+)/pdf', ktj_proxy),
    path('admin/', admin.site.urls),
    path('auth/', include(rest_framework.urls)),
    path('docs/', get_swagger_view(title='MVJ API')),
]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
