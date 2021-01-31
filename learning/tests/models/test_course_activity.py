#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
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
from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.models import Activity, Course


class CourseActivityTest(TestCase):

    def setUp(self):
        get_user_model().objects.create_user(id=1, username="william-shakespeare")
        get_user_model().objects.create_user(id=2, username="emily-dickinson")
        get_user_model().objects.create_user(id=3, username="h-p-lovecraft")
        get_user_model().objects.create_user(id=4, username="arthur-conan-doyle")
        get_user_model().objects.create_user(id=5, username="leo-tolstoy")

        self.activity1 = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )

        self.public_course = Course.objects.create(
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
        )
