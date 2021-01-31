#
# Copyright (C) 2019-2020 Guillaume Bernard <guillaume.bernard@koala-lms.org>
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
import abc
from enum import Enum
from typing import Set

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _


class ObjectPermissionManagerMixin:
    """
    This mixin implements a simple way to manage object permission for single users. This extends the Django
    authentication system in order to provide a per-object permission system.

    Read the Wiki for more information: https://gitlab.com/koala-lms/django-learning/-/wikis/Contribution/Manage%20Permissions
    """

    class PermissionMessage(Enum):
        """
        This enumeration contains the permission messages that could be shown to a user. Items can be added
        in this enumeration, depending on the permissions that are available for the subclass.
        """
        ADD = _("Can add the object")
        VIEW = _("Can view the object")
        CHANGE = _("Can change the object")
        DELETE = _("Can delete the object")

    def _make_full_permission(self, permission: str) -> str:
        """
        Transform a simple permission, like “add”, and adapt it to the current object, with the form of
        “<permission>_<object_type>”. “<object_type>” is the lowercase name of the class. For instance, the “add”
        permission on “MySuperClass” will be “add_mysuperclass”.

        :param permission: the simple permission string: “add”, “check”, “view”, etc.
        :type permission: str
        :return: a full permission string, containing the object name as suffix and permission as prefix
        :rtype: str
        """
        return "{permission}_{object_type}".format(permission=permission, object_type=type(self).__name__.lower())

    def _make_perms(self, permissions: Set[str]) -> Set[str]:
        """
        Transform a set of simple permissions into a set of full permissions, with the class name as prefix.

        :param permissions: the set of simple permission to transform
        :type permissions: Set[str]
        :return: a set of full permission, with the class name as suffix.
        :rtype: Set[str]
        """
        return {self._make_full_permission(permission) for permission in permissions}

    def get_user_perms(self, user: get_user_model()) -> Set[str]:
        """
        Get the full permissions for a given user. This consists of getting all the authorization for this user adapted
        to this current object, in the form of “<permission>_<object_type>”.

        :param user: the user for which to retrieve permissions
        :type user: get_user_model()
        :return: the set of permissions for this user.
        :rtype: Set[str]
        """
        return self._make_perms(self._get_user_perms(user))

    @abc.abstractmethod
    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        """
        Get all the simple permissions for this user. This means giving a set of simple permissions, without any
        suffix and giving the user permissions.

        .. note:: This has to be implemented in subclasses. This method is used by the “get_user_perms” function.

        :param user: the user for which to retrieve permissions
        :type user: get_user_model()
        :return: the set of simple permissions for this user.
        :rtype: Set[str]
        """
        raise NotImplementedError()

    def user_can_view(self, user: get_user_model()) -> bool:
        """
        Check whether the given user has the “view permission” on this object.

        :param user: the user for which to test the permission
        :type user: get_user_model()
        :return: True is the user has the given permission on the object
        :rtype: bool
        """
        return self._make_full_permission("view") in self.get_user_perms(user)

    def user_can_add(self, user: get_user_model()) -> bool:
        """
        Check whether the given user has the “add permission” on this object.

        :param user: the user for which to test the permission
        :type user: get_user_model()
        :return: True is the user has the given permission on the object
        :rtype: bool
        """
        return self._make_full_permission("add") in self.get_user_perms(user)

    def user_can_change(self, user: get_user_model()) -> bool:
        """
        Check whether the given user has the “change permission” on this object.

        :param user: the user for which to test the permission
        :type user: get_user_model()
        :return: True is the user has the given permission on the object
        :rtype: bool
        """
        return self._make_full_permission("change") in self.get_user_perms(user)

    def user_can_delete(self, user: get_user_model()) -> bool:
        """
        Check whether the given user has the “delete permission” on this object.

        :param user: the user for which to test the permission
        :type user: get_user_model()
        :return: True is the user has the given permission on the object
        :rtype: bool
        """
        return self._make_full_permission("delete") in self.get_user_perms(user)

    def user_can(self, permission: str, user: get_user_model()) -> bool:
        """
        Check whether the given user has the right given by “permission” on this object.

        :param permission: the short permission to check: “add”, “change”, “update”, etc.
        :type permission: str
        :param user: the user for which to test the permission
        :type user: get_user_model()
        :return: True is the user has the given permission on the object
        :rtype: bool
        """
        return self._make_full_permission(permission) in self.get_user_perms(user)
