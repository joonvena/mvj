from decimal import Decimal

from django.contrib.gis.db import models
from django.db import connection, transaction
from django.db.models import Max, Sum
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField
from sequences import get_next_value

from leasing.enums import (
    InfillDevelopmentCompensationState,
    InvoiceState,
    InvoiceType,
    LandUseAgreementAttachmentType,
    LandUseAgreementLitigantContactType,
    LandUseContractType,
)
from leasing.models.contact import Contact
from leasing.models.decision import DecisionMaker
from leasing.models.land_area import AbstractAddress, Plot
from leasing.models.lease import District, Municipality
from leasing.utils import calculate_increase_with_360_day_calendar
from users.models import User

from .mixins import NameModel, TimeStampedSafeDeleteModel


class LandUseAgreementType(NameModel):
    """
    In Finnish: Tyyppi
    """

    identifier = models.CharField(verbose_name=_("Identifier"), max_length=255)


class LandUseAgreementStatus(NameModel):
    """
    In Finnish: Olotila
    """


class LandUseAgreementDefinition(NameModel):
    """
    In Finnish: Määritelmä
    """


class LandUseAgreementIdentifier(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maankäyttösopimustunnus
    """

    # In Finnish: Tyyppi
    type = models.ForeignKey(
        LandUseAgreementType,
        verbose_name=_("Land use agreement type"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Kaupunki
    municipality = models.ForeignKey(
        Municipality,
        verbose_name=_("Municipality"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Kaupunginosa
    district = models.ForeignKey(
        District, verbose_name=_("District"), related_name="+", on_delete=models.PROTECT
    )

    # In Finnish: Juokseva numero
    sequence = models.PositiveIntegerField(verbose_name=_("Sequence number"))

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement identifier")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement identifiers"
        )
        unique_together = ("type", "municipality", "district", "sequence")

    def __str__(self):
        """Returns the land use agreement identifier as a string

        The Land use agreement identifier is constructed out of the type identifier, municipality,
        district, and sequence, in that order. For example, the identifier
        for a land use agreement (MA) in Helsinki (1), Vallila (22), and sequence
        number 1 would be MA122-1.
        """
        return "{}{}{:02}-{}".format(
            self.type.identifier,
            self.municipality.identifier,
            int(self.district.identifier),
            self.sequence,
        )


class LandUseAgreementCompensations(NameModel):
    """
    In Finnish: Maankäyttökorvaus
    """

    cash_compensation = models.DecimalField(
        verbose_name=_("Cash compensation"), decimal_places=2, max_digits=12
    )
    land_compensation = models.DecimalField(
        verbose_name=_("Land compensation"), decimal_places=2, max_digits=12
    )

    other_compensation = models.DecimalField(
        verbose_name=_("Other compensation"), decimal_places=2, max_digits=12
    )
    first_installment_increase = models.DecimalField(
        verbose_name=_("First installment increase"), decimal_places=2, max_digits=12
    )

    street_acquisition_value = models.DecimalField(
        verbose_name=_("Street acquisition value"), decimal_places=2, max_digits=12
    )

    street_area = models.PositiveIntegerField()
    park_acquisition_value = models.DecimalField(
        verbose_name=_("Park acquisition value"), decimal_places=2, max_digits=12
    )

    park_area = models.PositiveIntegerField()
    other_acquisition_value = models.DecimalField(
        verbose_name=_("Other acquisition value"), decimal_places=2, max_digits=12
    )

    other_area = models.PositiveIntegerField()


class LandUseAgreement(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maankäyttösopimus
    """

    # In Finnish: Tunnus
    identifier = models.OneToOneField(
        LandUseAgreementIdentifier,
        verbose_name=_("Land use agreement identifier"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Kaupunki
    municipality = models.ForeignKey(
        Municipality,
        verbose_name=_("Municipality"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Kaupunginosa
    district = models.ForeignKey(
        District, verbose_name=_("District"), related_name="+", on_delete=models.PROTECT
    )

    # In Finnish: Määritelmä
    definition = models.ForeignKey(
        LandUseAgreementDefinition,
        verbose_name=_("Land use agreement definition"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Olotila
    status = models.ForeignKey(
        LandUseAgreementStatus,
        verbose_name=_("Land use agreement status"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Tyyppi
    type = models.ForeignKey(
        LandUseAgreementType,
        verbose_name=_("Land use agreement type"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Valmistelija
    preparer = models.ForeignKey(
        User,
        verbose_name=_("Preparer"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Sopimuksen tyyppi
    land_use_contract_type = EnumField(
        LandUseContractType,
        verbose_name=_("Contract type"),
        null=True,
        blank=True,
        max_length=30,
    )

    # In Finnish: Arvioitu toteutumisvuosi
    estimated_completion_year = models.PositiveSmallIntegerField(
        verbose_name=_("Estimated completion year"), null=True, blank=True
    )

    # In Finnish: Arvioitu esittelyvuosi
    estimated_introduction_year = models.PositiveSmallIntegerField(
        verbose_name=_("Estimated introduction year"), null=True, blank=True
    )

    # In Finnish: Hankealue
    project_area = models.CharField(
        verbose_name=_("Project area"), null=True, blank=True, max_length=255
    )

    # In Finnish: Asemakaavan diaarinumero
    plan_reference_number = models.CharField(
        verbose_name=_("Plan reference number"), null=True, blank=True, max_length=255
    )

    # In Finnish: Asemakaavan nro.
    plan_number = models.CharField(
        verbose_name=_("Plan number"), max_length=255, null=True, blank=True
    )

    # In Finnish: Päättäjä
    plan_acceptor = models.ForeignKey(
        DecisionMaker,
        verbose_name=_("Plan acceptor"),
        related_name="land_use_agreements",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Asemakaavan lainvoimaisuuspvm
    plan_lawfulness_date = models.DateField(
        verbose_name=_("Plan lawfulness date"), null=True, blank=True
    )

    # In Finnish: Kiinteistöt
    plots = models.ManyToManyField(Plot)

    # In Finnish: Asemakaavan käsittelyvaihe
    state = EnumField(
        InfillDevelopmentCompensationState,
        verbose_name=_("State"),
        null=True,
        blank=True,
        max_length=30,
    )

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement")
        verbose_name_plural = pgettext_lazy("Model name", "Land use agreements")

    def __str__(self):
        return "Land use agreement #{}".format(self.id)

    @transaction.atomic
    def create_identifier(self):
        if self.identifier_id:
            return

        if not self.type or not self.municipality or not self.district:
            return

        # lock LandUseAgreementIdentifier table to prevent a (theoretically) possible
        # race condition when increasing the sequence
        with connection.cursor() as cursor:
            cursor.execute("LOCK TABLE %s" % self._meta.db_table)

        max_sequence = LandUseAgreementIdentifier.objects.filter(
            type=self.type, municipality=self.municipality, district=self.district
        ).aggregate(Max("sequence"))["sequence__max"]

        if not max_sequence:
            max_sequence = 0

        identifier = LandUseAgreementIdentifier.objects.create(
            type=self.type,
            municipality=self.municipality,
            district=self.district,
            sequence=max_sequence + 1,
        )

        self.identifier = identifier

    def save(self, *args, **kwargs):
        self.create_identifier()
        super().save(*args, **kwargs)


def get_attachment_file_upload_to(instance, filename):
    return "/".join(
        [
            "land_use_agreement_attachments",
            str(instance.land_use_agreement.id),
            filename,
        ]
    )


class LandUseAgreementAttachment(TimeStampedSafeDeleteModel):
    """
    In Finnish: Liitetiedosto
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement, related_name="attachments", on_delete=models.PROTECT
    )

    # In Finnish: Tyyppi
    type = EnumField(
        LandUseAgreementAttachmentType, verbose_name=_("Type"), max_length=30
    )

    # In Finnish: Tiedosto
    file = models.FileField(
        upload_to=get_attachment_file_upload_to, blank=False, null=False
    )

    # In Finnish: Lataaja
    uploader = models.ForeignKey(
        User, verbose_name=_("Uploader"), related_name="+", on_delete=models.PROTECT
    )

    # In Finnish: Latausaika
    uploaded_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Time uploaded")
    )

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement attachment")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement attachments"
        )


class LandUseAgreementEstate(NameModel):
    """
    In Finnish: Kohde
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="estate_ids",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    estate_id = models.CharField(verbose_name=_("Estate id"), max_length=50)


class LandUseAgreementDecisionType(NameModel):
    """
    In Finnish: Maankäyttösopimuspäätöksen tyyppi
    """

    class Meta(NameModel.Meta):
        verbose_name = pgettext_lazy("Model name", "Land use agreement decision type")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement decision types"
        )


class LandUseAgreementDecision(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maankäyttösopimuspäätös
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="decisions",
        on_delete=models.PROTECT,
    )

    # In Finnish: Diaarinumero
    reference_number = models.CharField(
        verbose_name=_("Reference number"), null=True, blank=True, max_length=255
    )

    # In Finnish: Päättäjä
    decision_maker = models.ForeignKey(
        DecisionMaker,
        verbose_name=_("Decision maker"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Päätöspäivämäärä
    decision_date = models.DateField(
        verbose_name=_("Decision date"), null=True, blank=True
    )

    # In Finnish: Pykälä
    section = models.CharField(
        verbose_name=_("Section"), null=True, blank=True, max_length=255
    )

    # In Finnish: Maankäyttösopimuspäätöksen tyyppi
    type = models.ForeignKey(
        LandUseAgreementDecisionType,
        verbose_name=_("Type"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Selite
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement decision")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement decisions"
        )


class LandUseAgreementDecisionConditionType(NameModel):
    """
    In Finnish: Maankäyttösopimuspäätöksen ehtotyyppi
    """

    class Meta(NameModel.Meta):
        verbose_name = pgettext_lazy(
            "Model name", "Land use agreement decision condition type"
        )
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement decision condition types"
        )


class LandUseAgreementDecisionCondition(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maankäyttösopimuspäätöksen ehto
    """

    # In Finnish: Päätös
    decision = models.ForeignKey(
        LandUseAgreementDecision,
        verbose_name=_("Decision"),
        related_name="conditions",
        on_delete=models.PROTECT,
    )

    # In Finnish: Ehtotyyppi
    type = models.ForeignKey(
        LandUseAgreementDecisionConditionType,
        verbose_name=_("Type"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Valvontapäivämäärä
    supervision_date = models.DateField(
        verbose_name=_("Supervision date"), null=True, blank=True
    )

    # In Finnish: Valvottu päivämäärä
    supervised_date = models.DateField(
        verbose_name=_("Supervised date"), null=True, blank=True
    )

    # In Finnish: Selite
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    recursive_get_related_skip_relations = ["decision"]

    class Meta:
        verbose_name = pgettext_lazy(
            "Model name", "Land use agreement decision condition"
        )
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement decision conditions"
        )


class LandUseAgreementAddress(AbstractAddress):
    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="addresses",
        on_delete=models.CASCADE,
    )

    # In Finnish: Ensisijainen osoite
    is_primary = models.BooleanField(verbose_name=_("Is primary?"), default=False)

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement address")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement addresses"
        )


class LandUseAgreementConditionFormOfManagement(NameModel):
    """
    In Finnish: Maankäyttösopimuksen ehdon hallintamuoto
    """


class LandUseAgreementCondition(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maankäyttösopimuksen ehto
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="conditions",
        on_delete=models.PROTECT,
    )

    # In Finnish: Maankäyttösopimuksen ehdon tyyppi
    form_of_management = models.ForeignKey(
        LandUseAgreementConditionFormOfManagement,
        verbose_name=_("Form of management"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Velvoite k-m2
    obligated_area = models.PositiveIntegerField(
        verbose_name=_("Obligated area (f-m2)")
    )

    # In Finnish: Toteutunut k-m2
    actualized_area = models.PositiveIntegerField(
        verbose_name=_("Actualized area (f-m2)")
    )

    # In Finnish: Subventio
    subvention_amount = models.PositiveIntegerField(verbose_name=_("Subvention amount"))

    # In Finnish: Korvaus %
    compensation_pc = models.PositiveSmallIntegerField(
        verbose_name=_("Compensation percent")
    )

    # In Finnish: Valvottava pvm
    supervision_date = models.DateField(verbose_name=_("Supervision date"))

    # In Finnish: Valvottu pvm
    supervised_date = models.DateField(verbose_name=_("Supervised date"))


class LandUseAgreementLitigant(TimeStampedSafeDeleteModel):
    """
    In Finnish: Osapuoli
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="litigants",
        on_delete=models.CASCADE,
    )

    # In Finnish: Viite
    reference = models.CharField(
        verbose_name=_("Section"), null=True, blank=True, max_length=255
    )

    contacts = models.ManyToManyField(
        Contact,
        through="leasing.LandUseAgreementLitigantContact",
        related_name="litigants",
    )

    recursive_get_related_skip_relations = ["land_use_agreement", "contacts"]

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement litigant")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement litigants"
        )


class LandUseAgreementLitigantContact(TimeStampedSafeDeleteModel):
    land_use_agreement_litigant = models.ForeignKey(
        LandUseAgreementLitigant,
        verbose_name=_("Land use agreement litigant"),
        on_delete=models.PROTECT,
    )

    # In Finnish: Asiakas
    contact = models.ForeignKey(
        Contact, verbose_name=_("Contact"), on_delete=models.PROTECT,
    )

    # In Finnish: Kontaktin tyyppi
    type = EnumField(
        LandUseAgreementLitigantContactType,
        verbose_name=_("Contact type"),
        max_length=30,
    )

    # In Finnish: Alkupäivämäärä
    start_date = models.DateField(verbose_name=_("Start date"), null=True, blank=True)

    # In Finnish: Loppupäivämäärä
    end_date = models.DateField(verbose_name=_("End date"), null=True, blank=True)

    recursive_get_related_skip_relations = ["land_use_agreement_litigant"]

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Land use agreement litigant")
        verbose_name_plural = pgettext_lazy(
            "Model name", "Land use agreement litigants"
        )

    def __str__(self):
        return "LandUseAgreementLitigantContact id: {} contact: {} period: {} - {}".format(
            self.id, self.contact, self.start_date, self.end_date
        )


class LandUseAgreementReceivableType(models.Model):
    """
    In Finnish: Saamislaji
    """

    name = models.CharField(verbose_name=_("Name"), max_length=255)
    sap_material_code = models.CharField(
        verbose_name=_("SAP material code"), null=True, blank=True, max_length=255
    )
    sap_order_item_number = models.CharField(
        verbose_name=_("SAP order item number"), null=True, blank=True, max_length=255
    )
    is_active = models.BooleanField(verbose_name=_("Is active?"), default=True)

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Receivable type")
        verbose_name_plural = pgettext_lazy("Model name", "Receivable types")

    def __str__(self):
        return self.name


class LandUseAgreementInvoice(TimeStampedSafeDeleteModel):
    """
    In Finnish: Lasku
    """

    land_use_agreement = models.ForeignKey(
        LandUseAgreement,
        verbose_name=_("Land use agreement"),
        related_name="invoices",
        on_delete=models.PROTECT,
    )

    # In Finnish: Laskutettu määrä
    billed_amount = models.DecimalField(
        verbose_name=_("Billed amount"), max_digits=10, decimal_places=2, default=0
    )

    # In Finnish: Hyvitetty lasku
    credited_invoice = models.ForeignKey(
        "self",
        verbose_name=_("Credited invoice"),
        related_name="credit_invoices",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Eräpäivä
    due_date = models.DateField(verbose_name=_("Due date"), null=True, blank=True)

    # In Finnish: Laskutuspvm
    invoicing_date = models.DateField(
        verbose_name=_("Invoicing date"), null=True, blank=True
    )

    # In Finnish: Laskun numero
    number = models.PositiveIntegerField(
        verbose_name=_("Number"), unique=True, null=True, blank=True
    )

    # In Finnish: Maksamaton määrä
    outstanding_amount = models.DecimalField(
        verbose_name=_("Outstanding amount"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # In Finnish: Laskunsaaja
    recipient = models.ForeignKey(
        Contact, verbose_name=_("Recipient"), related_name="+", on_delete=models.PROTECT
    )

    # In Finnish: Laskun tila
    state = EnumField(
        InvoiceState, verbose_name=_("State"), max_length=30, default=InvoiceState.OPEN
    )

    # In Finnish: Maksupäivä
    paid_date = models.DateField(verbose_name=_("Paid date"), null=True, blank=True)

    # In Finnish: Lähetyspäivä
    sent_date = models.DateField(verbose_name=_("Sent date"), null=True, blank=True)

    # In Finnish: Lähetetty SAP:iin
    sent_to_sap_at = models.DateTimeField(
        verbose_name=_("Sent to SAP at"), null=True, blank=True
    )

    # In Finnish: Laskun pääoma
    # TODO: Remove column and calculate total on-the-fly
    total_amount = models.DecimalField(
        verbose_name=_("Total amount"), max_digits=10, decimal_places=2, default=0
    )

    # In Finnish: Laskun tyyppi
    type = EnumField(
        InvoiceType, verbose_name=_("Type"), max_length=30, default=InvoiceType.CHARGE
    )

    def generate_number(self):
        if self.number:
            return self.number

        with transaction.atomic():
            self.number = get_next_value("invoice_numbers", initial_value=1000000)
            self.save()

        return self.number

    def update_amounts(self):
        for row in self.rows.all():
            row.update_amount()

        rows_sum = self.rows.aggregate(sum=Sum("amount"))["sum"]
        if not rows_sum:
            rows_sum = Decimal(0)

        self.billed_amount = rows_sum
        self.total_amount = rows_sum

        payments_total = self.payments.aggregate(sum=Sum("paid_amount"))["sum"]
        if not payments_total:
            payments_total = Decimal(0)

        # Aggregating like this ignores the manager (i.e. includes deleted rows which we don't want):
        # total_credited_amount = self.credit_invoices.aggregate(sum=Sum("rows__amount"))["sum"]
        # ... so we have to iterate the rows and tally the sum by hand
        total_credited_amount = Decimal(0)
        for credit_inv in self.credit_invoices.all():
            for row in credit_inv.rows.all():
                total_credited_amount += row.amount

        self.outstanding_amount = max(
            Decimal(0), self.billed_amount - payments_total - total_credited_amount,
        )
        # Don't mark as refunded unless credited amount is nonzero
        if total_credited_amount != Decimal(0) and total_credited_amount.compare(
            self.billed_amount
        ) != Decimal(-1):
            self.state = InvoiceState.REFUNDED
        elif self.type == InvoiceType.CHARGE and self.outstanding_amount == Decimal(0):
            self.state = InvoiceState.PAID

        self.save()


class LandUseAgreementInvoiceRow(TimeStampedSafeDeleteModel):
    """
    In Finnish: Rivi laskulla
    """

    # In Finnish: Lasku
    invoice = models.ForeignKey(
        LandUseAgreementInvoice,
        verbose_name=_("Invoice"),
        related_name="rows",
        on_delete=models.CASCADE,
    )

    # In Finnish: Osapuoli
    litigant = models.ForeignKey(
        LandUseAgreementLitigant,
        verbose_name=_("Litigant"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    # In Finnish: Saamislaji
    receivable_type = models.ForeignKey(
        LandUseAgreementReceivableType,
        verbose_name=_("Receivable type"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    # In Finnish: Laskutettava määrä
    amount = models.DecimalField(
        verbose_name=_("Amount"), max_digits=10, decimal_places=2, default=0
    )

    # In Finnish: Korvauksen määrä €
    compensation_amount = models.DecimalField(
        verbose_name=_("Compensation amount"),
        decimal_places=2,
        max_digits=12,
        default=0,
    )

    # In Finnish: Selite
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    # In Finnish: Korotuksen määrä %
    increase_percentage = models.DecimalField(
        verbose_name=_("Increase percentage"),
        decimal_places=2,
        max_digits=12,
        default=0,
    )

    # In Finnish: Asemakaavan lainvoimaisuuspvm
    plan_lawfulness_date = models.DateField(
        verbose_name=_("Plan lawfulness date"), null=True, blank=True
    )

    # In Finnish: Allekirjoituspvm
    sign_date = models.DateField(verbose_name=_("Sign date"), null=True, blank=True)

    recursive_get_related_skip_relations = ["invoice"]

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Invoice row")
        verbose_name_plural = pgettext_lazy("Model name", "Invoice rows")

    def update_amount(self):
        self.amount = calculate_increase_with_360_day_calendar(
            self.sign_date,
            self.plan_lawfulness_date,
            self.increase_percentage,
            self.compensation_amount,
        )
        self.save()


class LandUseAgreementInvoicePayment(TimeStampedSafeDeleteModel):
    """
    In Finnish: Maksusuoritus
    """

    # In Finnish: Lasku
    invoice = models.ForeignKey(
        LandUseAgreementInvoice,
        verbose_name=_("Invoice"),
        related_name="payments",
        on_delete=models.CASCADE,
    )

    # In Finnish: Maksettu määrä
    paid_amount = models.DecimalField(
        verbose_name=_("Paid amount"), max_digits=10, decimal_places=2
    )

    # In Finnish: Maksettu pvm
    paid_date = models.DateField(verbose_name=_("Paid date"))

    # In Finnish: Arkistointitunnus
    filing_code = models.CharField(
        verbose_name=_("Name"), null=True, blank=True, max_length=35
    )

    recursive_get_related_skip_relations = ["invoice"]

    class Meta:
        verbose_name = pgettext_lazy("Model name", "Invoice payment")
        verbose_name_plural = pgettext_lazy("Model name", "Invoice payments")
