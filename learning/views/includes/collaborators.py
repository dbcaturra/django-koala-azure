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
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotFound, HttpResponseNotAllowed
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import ProcessFormView, FormMixin

from learning.exc import UserIsAlreadyStudent, UserIsAlreadyCollaborator, UserIsAlreadyAuthor, LearningError
from learning.forms import AddCollaboratorOnBasicModelMixin, UserPKForm, CourseCollaboratorUpdateRoleForm, \
    ActivityCollaboratorUpdateRoleForm, ResourceCollaboratorUpdateRoleForm
from learning.models import extract_all_included_objects, CollaboratorRole, Course, Activity, Resource
from learning.views.helpers import PaginatorFactory, InvalidFormHandlerMixin


class BasicModelDetailCollaboratorListViewMixin(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin):
    """
    Mixin to view collaborators of a BasicObjectMixin.

    .. caution:: Viewing collaborators requires the **view_collaborators** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("view_collaborators", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to view collaborators of this %(object)s.")
            % {"object": _(self.object.__class__.__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailCollaboratorsListView(BasicModelDetailCollaboratorListViewMixin, FormView):
    """
    View collaborators on a course in a HTML page.
    """
    form_class = AddCollaboratorOnBasicModelMixin

    # noinspection PyMissingOrEmptyDocstring,PyUnresolvedReferences
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            PaginatorFactory.get_paginator_as_context(
                self.object.object_collaborators.order_by('collaborator__first_name'),
                self.request.GET,
                nb_per_page=10
            )
        )
        context['number_collaborator'] = self.object.object_collaborators.count()

        return context


class BasicModelCollaboratorsAddViewMixin(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin):
    """
    Mixin to add a collaborator on a course.

    .. caution:: Adding a collaborator requires the **add_collaborator** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("add_collaborator", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to add a collaborator on this %(object)s.")
            % {"object": _(self.object.__class__.__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailCollaboratorsAddView(BasicModelCollaboratorsAddViewMixin, InvalidFormHandlerMixin, FormView):
    """
    Add a collaborator on a course in a HTML page.
    """
    form_class = AddCollaboratorOnBasicModelMixin

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring,PyUnresolvedReferences
    def form_valid(self, form):
        username = form.cleaned_data.get("username", None)
        try:
            role = CollaboratorRole[form.cleaned_data.get("roles", CollaboratorRole.NON_EDITOR_TEACHER)]
            user = get_user_model().objects.filter(username=username).get()
            propagate = form.cleaned_data.get("propagate", False)

            # Add the collaborator on this object
            self.object.add_collaborator(user, role)

            # Propagate to all the included objects on which the user in request has add_collaborator permission
            if propagate:
                for included_object in set(extract_all_included_objects(self.object)):
                    if included_object.user_can("add_collaborator", self.request.user) and \
                            user not in included_object.object_collaborators.all():
                        included_object.add_collaborator(user, role)

            messages.success(
                self.request,
                _("%(user)s does now collaborates on the %(object)s as a %(role)s.")
                % {"user": user, "object": _(self.object.__class__.__name__.lower()), "role": role.value}
            )
        except ObjectDoesNotExist:
            messages.error(
                self.request, _("This user does not exists.")
            )
        except (UserIsAlreadyStudent, UserIsAlreadyCollaborator, UserIsAlreadyAuthor) as ex:
            messages.warning(self.request, ex)
        except LearningError as ex:
            messages.error(self.request, ex)
        except KeyError:
            pass
        return redirect(self.get_success_url(), slug=self.object.slug)

    # noinspection PyMissingOrEmptyDocstring, PyUnresolvedReferences
    def form_invalid(self, form):
        super().form_invalid(form)
        return redirect(self.get_success_url(), slug=self.object.slug)


class BasicModelDetailCollaboratorsChangeViewMixin(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin):
    """
    Mixin to change a collaborator on a course.

    .. caution:: Changing a collaborator on a course requires the **change_collaborator** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("change_collaborator", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to change collaborators on this %(object)s.")
            % {"object": _(self.object.__class__.__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailCollaboratorsChangeView(BasicModelDetailCollaboratorsChangeViewMixin,
                                              InvalidFormHandlerMixin, UpdateView):
    """
    Change a collaborator on a course in a HTML page.
    """

    # noinspection PyMissingOrEmptyDocstring
    def get_form_depending_on_object(self):
        form = None
        if isinstance(self.object, Course):
            form = CourseCollaboratorUpdateRoleForm
        elif isinstance(self.object, Activity):
            form = ActivityCollaboratorUpdateRoleForm
        elif isinstance(self.object, Resource):
            form = ResourceCollaboratorUpdateRoleForm
        return form

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def post(self, request, *args, **kwargs):
        user_pk_form = UserPKForm(self.request.POST or None)
        if user_pk_form.is_valid():
            collaborator = get_object_or_404(get_user_model(), pk=user_pk_form.cleaned_data.get("user_pk"))
            object_collaborator = self.object.object_collaborators.get(collaborator=collaborator)

            # Build the form
            form = self.get_form_depending_on_object()(request.POST, initial={"role": object_collaborator.role})
            form.instance.collaborator = collaborator
            setattr(form.instance, self.object.__class__.__name__.lower(), self.object)

            if form.is_valid():
                self.form_valid(form)
            else:
                self.form_invalid(form)
            return redirect(self.get_success_url(), slug=self.object.slug)
        return HttpResponseNotFound(user_pk_form.errors.get("user_pk"))

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        if form.has_changed():
            object_collaborator = self.object.object_collaborators.filter(
                collaborator=form.instance.collaborator
            ).get()
            old_role = object_collaborator.role
            self.object.change_collaborator_role(object_collaborator.collaborator,
                                                 CollaboratorRole[form.instance.role])
            messages.success(
                self.request,
                _("Role for user “%(user)s“ changed from “%(old_role)s” to “%(new_role)s”") % {
                    "user": object_collaborator.collaborator,
                    "old_role": CollaboratorRole[old_role].value,
                    "new_role": CollaboratorRole[form.instance.role].value
                })

    # noinspection PyMissingOrEmptyDocstring
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class BasicModelDetailCollaboratorsDeleteViewMixin(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin):
    """
    Mixin to delete a collaborator from a course.

    .. note:: Deleting a collaborator from a course requires the **delete_collaborator** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("delete_collaborator", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to delete collaborators on this %(object)s.")
            % {"object": _(self.object.__class__.__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailCollaboratorsDeleteView(BasicModelDetailCollaboratorsDeleteViewMixin, FormMixin,
                                              ProcessFormView):
    """
    Delete a collaborator from a course in a HTML page.
    """

    # noinspection PyMissingOrEmptyDocstring,PyUnresolvedReferences
    def post(self, request, *args, **kwargs):
        user_pk_form = UserPKForm(self.request.POST or None)
        if user_pk_form.is_valid():
            collaborator = get_object_or_404(get_user_model(), pk=user_pk_form.cleaned_data.get("user_pk"))
            self.object.remove_collaborator(collaborator)
            messages.success(
                self.request,
                _("The collaborator “%(collaborator)s” has been removed from %(object)s “%(entity)s”.")
                % {"collaborator": collaborator, "object": _(self.object.__class__.__name__.lower()),
                   "entity": self.object}
            )
            return redirect(self.get_success_url(), slug=self.object.slug)
        return HttpResponseNotFound(user_pk_form.errors.get("user_pk"))

    # noinspection PyMissingOrEmptyDocstring
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
