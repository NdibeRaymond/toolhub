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
from django_elasticsearch_dsl.signals import RealTimeSignalProcessor

from safedelete.models import SafeDeleteModel
from safedelete.signals import post_softdelete


class SignalProcessor(RealTimeSignalProcessor):
    """Update index based on signals."""

    def handle_save(self, sender, instance, **kwargs):
        """Handle save."""
        if isinstance(instance, SafeDeleteModel):
            if instance.deleted is not None:
                # Ignore if instance is soft deleted
                return
        super().handle_save(sender, instance, **kwargs)

    def setup(self):
        """Setup signals."""
        super().setup()
        post_softdelete.connect(self.handle_delete)

    def teardown(self):
        """Teardown signals."""
        post_softdelete.disconnect(self.handle_delete)
        super().teardown()
