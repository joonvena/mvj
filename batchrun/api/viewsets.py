from enumfields.drf.serializers import EnumSupportSerializerMixin
from rest_framework import serializers, viewsets  # type: ignore

from .. import models


class Serializer(
    EnumSupportSerializerMixin, serializers.ModelSerializer  # type: ignore
):
    pass


class JobSerializer(Serializer):
    class Meta:
        model = models.Job
        fields = "__all__"


class JobViewSet(viewsets.ReadOnlyModelViewSet):  # type: ignore
    queryset = models.Job.objects.all()
    serializer_class = JobSerializer


class JobRunSerializer(Serializer):
    class Meta:
        model = models.JobRun
        fields = "__all__"


class JobRunViewSet(viewsets.ReadOnlyModelViewSet):  # type: ignore
    queryset = models.JobRun.objects.all_with_deleted()
    serializer_class = JobRunSerializer
    filterset_fields = ["exit_code"]


class JobRunLogEntrySerializer(Serializer):
    class Meta:
        model = models.JobRunLogEntry
        fields = "__all__"


class JobRunLogEntryViewSet(viewsets.ReadOnlyModelViewSet):  # type: ignore
    queryset = models.JobRunLogEntry.objects.all_with_deleted()
    serializer_class = JobRunLogEntrySerializer
    filterset_fields = ["run", "kind"]
