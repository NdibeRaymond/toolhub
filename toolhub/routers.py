# Copyright (c) 2020 Wikimedia Foundation and contributors.
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
from rest_framework import routers as drf_routers

import toolhub.apps.crawler.views as crawler_views
import toolhub.apps.toolinfo.views as toolinfo_views
import toolhub.apps.user.views as user_views


class ToolhubApiRootView(drf_routers.APIRootView):
    """Welcome to the API for Toolhub.

    This API provides access to Toolhub content and data in machine-readable
    formats.
    """


class Router(drf_routers.DefaultRouter):
    """Custom router."""

    APIRootView = ToolhubApiRootView


router = Router()
router.register("users", user_views.UserViewSet)
router.register("groups", user_views.GroupViewSet)
router.register("crawler/urls", crawler_views.UrlViewSet)
router.register("tools", toolinfo_views.ToolViewSet)
