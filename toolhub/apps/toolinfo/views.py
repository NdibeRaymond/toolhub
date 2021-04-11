# Copyright (c) 2021 Wikimedia Foundation and contributors.
# All Rights Reserved.
#
# This file is part of Toolhub.
#
# Toolhub is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Toolhub is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Toolhub.  If not, see <http://www.gnu.org/licenses/>.
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

import jsonpatch

from rest_framework import permissions
from rest_framework import response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException

from reversion.models import Version

import spdx_license_list

from .models import Tool
from .serializers import CreateToolSerializer
from .serializers import SpdxLicenseSerializer
from .serializers import ToolRevisionDetailSerializer
from .serializers import ToolRevisionDiffSerializer
from .serializers import ToolRevisionSerializer
from .serializers import ToolSerializer
from .serializers import UpdateToolSerializer


class ConflictingState(APIException):
    """Patch failed due to conflicting state."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = _("Failed to apply patch.")


@extend_schema_view(
    create=extend_schema(
        description=_("""Create a new tool."""),
        request=CreateToolSerializer,
        responses=ToolSerializer,
    ),
    retrieve=extend_schema(
        description=_("""Info for a specific tool."""),
    ),
    update=extend_schema(
        description=_("""Update info for a specific tool."""),
        request=UpdateToolSerializer,
        responses=ToolSerializer,
    ),
    partial_update=extend_schema(
        exclude=True,
    ),
    destroy=extend_schema(
        description=_("""Delete a tool."""),
    ),
    list=extend_schema(
        description=_("""List all tools."""),
    ),
)
class ToolViewSet(viewsets.ModelViewSet):
    """Tools."""

    lookup_field = "name"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = {
        "name": ["exact", "contains", "startswith", "endswith"],
    }
    ordering_fields = ["name", "modified_date"]
    ordering = ["-modified_date"]

    def get_queryset(self):
        """Filter qs by current user when editing."""
        if self.request.method in ["DELETE", "PUT"]:
            return Tool.objects.filter(created_by=self.request.user)
        return Tool.objects.all()

    def get_serializer_class(self):
        """Use different serializers for input vs output."""
        if self.request.method == "POST":
            return CreateToolSerializer
        if self.request.method == "PUT":
            return UpdateToolSerializer
        return ToolSerializer


path_param_tool_name = OpenApiParameter(
    "tool_name",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.PATH,
    description=_("""Unique identifier for this tool."""),
)


@extend_schema_view(
    retrieve=extend_schema(
        description=_("""Get revision information."""),
        parameters=[path_param_tool_name],
        responses=ToolRevisionDetailSerializer,
    ),
    list=extend_schema(
        description=_("""List revisions."""),
        parameters=[path_param_tool_name],
        responses=ToolRevisionSerializer,
    ),
    diff=extend_schema(
        description=_("""Compare two revisions to find difference."""),
        parameters=[
            path_param_tool_name,
            OpenApiParameter(
                "other_id",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.PATH,
                description=_(
                    "A unique integer value identifying version "
                    "to diff against."
                ),
            ),
        ],
        responses=ToolRevisionDiffSerializer,
    ),
    revert=extend_schema(
        description=_("""Restore the tool to this revision."""),
        parameters=[
            path_param_tool_name,
        ],
        responses=ToolSerializer,
    ),
    undo=extend_schema(
        description=_("""Undo all changes made between two revisions."""),
        parameters=[
            path_param_tool_name,
            OpenApiParameter(
                "other_id",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.PATH,
                description=_(
                    "A unique integer value identifying version "
                    "to undo until."
                ),
            ),
        ],
        responses=ToolSerializer,
    ),
)
class ToolRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    """Historical revisions of a tool."""

    queryset = Version.objects.none()
    serializer_class = ToolRevisionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Filter queryset by Tool using path param."""
        tool = get_object_or_404(Tool, name=self.kwargs["tool_name"])
        qs = Version.objects.select_related("revision", "revision__user")
        qs = qs.get_for_object(tool)
        return qs

    def get_serializer_class(self):
        """Use different serializers for list vs retrieve."""
        if self.action == "retrieve":
            return ToolRevisionDetailSerializer
        return ToolRevisionSerializer

    def _get_patch(self, left, right):
        """Compute the JSON Patch between revisions."""
        data_left = ToolSerializer(left.field_dict).data
        data_right = ToolSerializer(right.field_dict).data
        # T279484: exclude modified_date from diff
        del data_left["modified_date"]
        del data_right["modified_date"]
        return jsonpatch.make_patch(data_left, data_right)

    def _update_tool(self, data, request):
        """Update our toolinfo record."""
        tool = get_object_or_404(Tool, name=self.kwargs["tool_name"])
        serializer = UpdateToolSerializer(
            tool, data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        tool = serializer.save()
        return response.Response(ToolSerializer(tool).data)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"diff/(?P<other_id>\d+)",
    )
    def diff(self, request, **kwargs):
        """Diff."""
        id_left = kwargs["pk"]
        id_right = kwargs["other_id"]
        qs = self.get_queryset()

        version_left = get_object_or_404(qs, pk=id_left)
        version_right = get_object_or_404(qs, pk=id_right)
        patch = self._get_patch(version_left, version_right)

        diff = ToolRevisionDiffSerializer(
            {
                "original": version_left,
                "operations": patch,
                "result": version_right,
            }
        )

        return response.Response(diff.data)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"revert",
    )
    def revert(self, request, **kwargs):
        """Revert."""
        rev_id = kwargs["pk"]
        qs = self.get_queryset()
        rev = get_object_or_404(qs, pk=rev_id)
        data = rev.field_dict
        data["comment"] = _(
            "Revert to revision %(rev_id)s dated %(datetime)s by %(user)s"
        ) % {
            "rev_id": rev_id,
            "datetime": rev.revision.date_created.strftime(
                "%Y-%m-%dT%H:%M:%S.%f%z"
            ),
            "user": rev.revision.user.username,
        }
        return self._update_tool(data, request)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"undo/(?P<other_id>\d+)",
    )
    def undo(self, request, **kwargs):
        """Undo."""
        id_left = kwargs["pk"]
        id_right = kwargs["other_id"]
        qs = self.get_queryset()

        version_left = get_object_or_404(qs, pk=id_left)
        version_right = get_object_or_404(qs, pk=id_right)
        patch = self._get_patch(version_left, version_right)

        head = qs.first()
        data = head.field_dict

        try:
            jsonpatch.apply_patch(data, patch, in_place=True)
        except jsonpatch.JsonPatchException as e:
            raise ConflictingState() from e

        data["comment"] = _(
            "Undo revisions from %(first_id)s to %(last_id)s"
        ) % {
            "first_id": id_left,
            "last_id": id_right,
        }
        return self._update_tool(data, request)


@extend_schema_view(
    retrieve=extend_schema(
        description=_("""Info for a specific SPDX license."""),
        request=SpdxLicenseSerializer,
        responses=SpdxLicenseSerializer,
        parameters=[
            OpenApiParameter("id", OpenApiTypes.STR, OpenApiParameter.PATH),
        ],
    ),
    list=extend_schema(
        description=_("""List all SPDX licenses."""),
        request=SpdxLicenseSerializer,
        responses=SpdxLicenseSerializer,
        parameters=[
            OpenApiParameter(
                "osi_approved", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                "fsf_approved", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                "deprecated", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
        ],
    ),
)
class SpdxViewSet(viewsets.ViewSet):
    """SPDX license information."""

    def _as_bool(self, value):
        """Cast a value to a boolean."""
        return str(value).lower() in ["true", "1", "yes"]

    def _filter_bool(self, request, src, qs, field):
        """Apply a boolean filter to a dict of licenses."""
        qs = request.query_params.get(qs, None)
        if qs is not None:
            qs = self._as_bool(qs)
            src = {k: v for k, v in src.items() if v[field] == qs}
        return src

    def list(self, request):  # noqa: A003
        """Get a list of license objects."""
        licenses = spdx_license_list.LICENSES
        licenses = self._filter_bool(
            request, licenses, "osi_approved", "isOsiApproved"
        )
        licenses = self._filter_bool(
            request, licenses, "fsf_approved", "isFsfLibre"
        )
        licenses = self._filter_bool(
            request, licenses, "deprecated", "isDeprecatedLicenseId"
        )

        serializer = SpdxLicenseSerializer(licenses.values(), many=True)
        return response.Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a single license object."""
        licenses = spdx_license_list.LICENSES
        try:
            serializer = SpdxLicenseSerializer(licenses[pk])
            return response.Response(serializer.data)
        except KeyError:
            return response.Response(
                {
                    "code": 4004,
                    "message": "Not found.",
                    "status_code": 404,
                    "errors": [
                        {"field": "detail", "message": "Not found."},
                    ],
                },
                status=status.HTTP_404_NOT_FOUND,
            )
