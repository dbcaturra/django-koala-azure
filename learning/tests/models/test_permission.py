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
from django.test import TestCase

from learning.permissions import ObjectPermissionManagerMixin


# noinspection SpellCheckingInspection
class ObjectPermissionManagerTest(TestCase):
    perms = ["view", "change", "delete", "add", "anything"]

    class FakeImplementation(ObjectPermissionManagerMixin):

        def _get_user_perms(self, user):
            return ObjectPermissionManagerTest.perms

    def setUp(self):
        self.fake = ObjectPermissionManagerTest.FakeImplementation()

    def test_make_simple_perms(self):
        for perm in self.perms:
            self.assertEqual("{}_fakeimplementation".format(perm), self.fake._make_full_permission(perm))

    def test_make_perms(self):
        new_perms = self.fake._make_perms(self.perms)
        self.assertEqual(len(self.perms), len(new_perms))
        for perm in self.perms:
            perm_str = "{}_fakeimplementation".format(perm)
            self.assertIn(perm_str, new_perms)

    def test_user_can(self):
        self.assertTrue(self.fake.user_can_view(None))
        self.assertTrue(self.fake.user_can_change(None))
        self.assertTrue(self.fake.user_can_delete(None))
        self.assertTrue(self.fake.user_can_add(None))
        self.assertTrue(self.fake.user_can("anything", None))
        self.assertFalse(self.fake.user_can("nothing", None))
