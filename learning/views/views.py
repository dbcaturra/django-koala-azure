#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
# Copyright (C) 2020 Louis Barbier <louis.barbier41@outlook.fr>
#
# This file is part of Koala LMS (Learning Management system)

# Koala LMS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# We make an extensive use of the Django framework, https://www.djangoproject.com/
#

from django.views.generic import TemplateView

from learning.models import Course
from learning.views.helpers import PaginatorFactory


class WelcomePageView(TemplateView):
    model = Course
    template_name = "learning/base.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        if self.request.user.is_authenticated:
            context.update(
                PaginatorFactory.get_paginator_as_context(
                    Course.objects.followed_by(self.request.user).all(),
                    self.request.GET, nb_per_page=6
                )
            )
        else:
            context.update(
                PaginatorFactory.get_paginator_as_context(
                    Course.objects.public().all(),
                    self.request.GET, nb_per_page=6
                )
            )
        return context
