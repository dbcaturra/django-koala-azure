#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
# Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, DeleteView, UpdateView, CreateView, TemplateView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import ProcessFormView

from learning.forms import ResourceCreateForm, ResourceUpdateForm, BasicSearchForm, ResourceObjectiveUpdateForm
from learning.models import Resource, get_max_upload_size, ResourceObjective, CollaboratorRole, ResourceCollaborator
from learning.views.helpers import PaginatorFactory, InvalidFormHandlerMixin
from learning.views.includes.collaborators import BasicModelDetailCollaboratorsListView, \
    BasicModelDetailCollaboratorsChangeView, BasicModelDetailCollaboratorsAddView, \
    BasicModelDetailCollaboratorsDeleteView
from learning.views.objective import ObjectObjectiveDetailMixin, BasicModelDetailObjectiveAddView, \
    ObjectObjectiveUpdateValidationView, BasicModelDetailObjectiveRemoveView, BasicModelDetailObjectiveUpdateView


class ResourceDetailMixin(PermissionRequiredMixin, SingleObjectMixin):
    """
    A mixin to provide united context or functions to resources views.

    .. caution:: Viewing a resource requires the **view_resource** permission.
    """
    model = Resource
    template_name = "learning/resource/detail.html"

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyMissingOrEmptyDocstring
    def has_permission(self):
        # noinspection PyUnresolvedReferences
        return self.get_object().user_can_view(self.request.user)

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add user specific elements in the context
        if self.request.user.is_authenticated:
            if self.request.user in self.object.collaborators.all():
                context["contribution"] = ResourceCollaborator.objects \
                    .get(collaborator=self.request.user, resource=self.object)
        return context


class ResourceDetailView(ResourceDetailMixin, PermissionRequiredMixin, DetailView):
    """
    View to show resource details
    """

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to access this resource."))
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["objectives"] = PaginatorFactory.get_paginator_as_context(
            ResourceObjective.objects.filter(resource=self.object).order_by("created").reverse(),
            self.request.GET,
            nb_per_page=6
        )
        context["user_is_teacher_non_editor"] = ResourceCollaborator.objects.filter(
            collaborator=self.request.user, resource=self.object, role=CollaboratorRole.NON_EDITOR_TEACHER.name
        ).exists()

        context["user_is_teacher_editor"] = ResourceCollaborator.objects.filter(
            collaborator=self.request.user, resource=self.object, role=CollaboratorRole.TEACHER.name
        ).exists()
        context["user_contribute"] = self.request.user in self.object.collaborators.all()
        context["user_is_author_of_object"] = self.request.user == self.object.author
        if self.request.user != self.object.author:
            context["auth_user"] = self.request.user
        return context


class ResourceCreateView(LoginRequiredMixin, InvalidFormHandlerMixin, CreateView):
    """
    View to create a new resource
    """
    model = Resource
    form_class = ResourceCreateForm
    template_name = "learning/resource/add.html"
    extra_context = {
        "media_upload_size": get_max_upload_size()
    }

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, _("Resource “%(resource)s” created.") % {"resource": form.instance.name})
        return super().form_valid(form)

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        return reverse_lazy("learning:resource/detail", kwargs={"slug": self.object.slug})


class ResourceUpdateViewMixin(LoginRequiredMixin, ResourceDetailMixin):
    """
    Mixin to update an existing activity

    .. caution:: Updating a resource requires the **change_resource** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.get_object().user_can_change(self.request.user)

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to change this resource."))
        return super().handle_no_permission()


class ResourceUpdateView(ResourceUpdateViewMixin, InvalidFormHandlerMixin, UpdateView):
    """
    Update an existing activity in a HTML page
    """
    form_class = ResourceUpdateForm
    template_name = "learning/resource/details/change.html"
    extra_context = {
        "media_upload_size": get_max_upload_size()
    }

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        if form.has_changed():
            messages.success(
                self.request, _("The resource “%(resource)s” has been updated.") % {"resource": self.object.name}
            )
        return super().form_valid(form)

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        return reverse_lazy("learning:resource/detail", kwargs={"slug": self.object.slug})


class ResourceDeleteViewMixin(LoginRequiredMixin, ResourceDetailMixin):
    """
    Mixin to delete a resource

    .. caution:: Deleting a resource requires the **delete_resource** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.get_object().user_can_delete(self.request.user)

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to delete this resource."))
        return super().handle_no_permission()


class ResourceDeleteView(ResourceDeleteViewMixin, DeleteView):
    """
    Delete a resource in a HTML page
    """
    success_url = reverse_lazy("learning:resource/my")
    template_name = "learning/resource/delete.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        messages.success(
            self.request, _("The resource ”%(resource)s” has been deleted.") % {"resource": self.object.name}
        )
        return super().get_success_url()


class ResourceListView(LoginRequiredMixin, TemplateView):
    """
    List the activities that the logged-on user is the author of.

    When action is performed, the context is filled with:

    * **form**: a BasicSearchForm instance, allowing you to search for specific words
    * **resources_page_obj,resources_has_obj**…: what is given by the PaginatorFactory to display resources owned \
                                                   by the user
    * **search_page_obj,search_has_obj**…: same but for the activity search result.
    """
    model = Resource
    template_name = "learning/resource/my_list.html"
    form_class = BasicSearchForm  # This is used to perform the search

    # pylint: disable=unused-argument
    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        # Add the paginator on favourite resources of the user.
        # Prefix is “favourite”: so object are “favourite_has_obj…”
        context.update(PaginatorFactory.get_paginator_as_context(
            Resource.objects.teacher_favourites_for(self.request.user),
            self.request.GET, prefix="favourite", nb_per_page=6)
        )

        # Add the paginator on resources where user is author
        context.update(PaginatorFactory.get_paginator_as_context(
            Resource.objects.written_by(self.request.user),
            self.request.GET, prefix="author", nb_per_page=6)
        )

        # Add the paginator on resources where user is a collaborator
        # FIXME: this should exclude favourite courses where the user contribute
        context.update(
            PaginatorFactory.get_paginator_as_context(
                ResourceCollaborator.objects.filter(collaborator=self.request.user),
                self.request.GET, prefix="contributor", nb_per_page=6
            )
        )

        # Execute the user query and add the paginator on query
        form = BasicSearchForm(data=self.request.GET)
        if form.is_valid() and form.cleaned_data.get("query", str()):
            context.update(PaginatorFactory.get_paginator_as_context(
                Resource.objects.taught_by(self.request.user, query=form.cleaned_data.get("query", str())),
                self.request.GET, prefix="search")
            )

        # Add the query form in the view
        context["form"] = form
        return context


class ResourceFavouriteListView(ResourceListView, InvalidFormHandlerMixin, ProcessFormView):

    def post(self, request, *args, **kwargs):
        teacher = self.request.user
        resource = get_object_or_404(Resource, slug=kwargs.get("resource_slug", None))
        if teacher in resource.favourite_for.all():
            resource.favourite_for.remove(teacher)
            messages.success(
                self.request,
                _("%(resource)s has been removed from your favourites resources.")
                % {"resource": resource.name}
            )
        else:
            resource.favourite_for.add(teacher)
            messages.success(
                self.request,
                _("%(resource)s has been added to your favourites resources.")
                % {"resource": resource.name}
            )
        return redirect("learning:resource/my")


class ResourceDetailUsageViewMixin(LoginRequiredMixin, ResourceDetailView):
    """
    Mixin to view which activities use this resource.

    .. caution:: Viewing activities that use this activities requires the **view_usage_resource** permission.
    """

    # noinspection PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.get_object().user_can("view_usage", self.request.user) and super().has_permission()

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request, _("You do not have the required permissions to view where this resource is used.")
        )
        return super().handle_no_permission()


class ResourceDetailUsageView(ResourceDetailUsageViewMixin):
    """
    View which activities use this resource in a HTML page.

    When action is performed, the context is filled with:

    * **page_obj,has_obj**…: what is given by the PaginatorFactory to display courses that use this resource.
    """
    template_name = "learning/resource/details/usage.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Activities where the resources is used
        context.update(PaginatorFactory.get_paginator_as_context(
            self.object.activities.all(), self.request.GET, nb_per_page=10)
        )
        return context


class ResourceDetailSimilarViewMixin(ResourceDetailView):
    """
    Mixin to view similar resources.

    .. caution:: Viewing similar resources requires the **view_similar_resource** permission.
    """

    # noinspection PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.get_object().user_can("view_similar", self.request.user) and super().has_permission()

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to view similar resources."))
        return super().handle_no_permission()


class ResourceDetailCollaboratorsListView(ResourceDetailMixin, BasicModelDetailCollaboratorsListView):
    """
    View collaborators of a resource in a HTML page.
    """
    template_name = "learning/resource/details/collaborators.html"


class ResourceDetailCollaboratorsAddView(BasicModelDetailCollaboratorsAddView, ResourceDetailMixin):
    """
    Add a collaborator of a resource in a HTML page.
    """
    success_url = "learning:resource/detail/collaborators"


class ResourceDetailCollaboratorsChangeView(BasicModelDetailCollaboratorsChangeView, ResourceDetailMixin):
    """
    Change a collaborator of a resource in a HTML page.
    """
    success_url = "learning:resource/detail/collaborators"


class ResourceDetailCollaboratorsDeleteView(BasicModelDetailCollaboratorsDeleteView, ResourceDetailMixin):
    """
    Delete a collaborator from a resource in a HTML page.
    """
    success_url = "learning:resource/detail/collaborators"


class ResourceDetailSimilarView(ResourceDetailSimilarViewMixin):
    """
    View similar resources in a HTML page. Similar resources are based on the resource tags.

    When action is performed, the context is filled with:

    * **page_obj,has_obj**…: what is given by the PaginatorFactory to display similar resources.

    .. note:: warning: The dependency we use to do so, django-taggit has a weird behaviour that can lead to an exception.
    """
    template_name = "learning/resource/details/similar.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # noinspection PyBroadException
        try:
            similar_list = [
                similar for similar in self.object.tags.similar_objects()
                if isinstance(similar, Resource) and similar.user_can_view(self.request.user)
            ]
            context.update(PaginatorFactory.get_paginator_as_context(similar_list, self.request.GET, nb_per_page=9))
        # django-taggit similar tags can have weird behaviour sometimes: https://github.com/jazzband/django-taggit/issues/80
        except Exception:
            messages.error(
                self.request,
                _("We’re having some problems finding similar resources… We try to fix this as soon as possible.")
            )
        return context


class ResourceDetailObjectiveListView(ObjectObjectiveDetailMixin, ResourceDetailView):
    """
    Lists the objectives in  Resource
    User can add objective from here
    """
    template_name = "learning/resource/details/objective.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(
            PaginatorFactory.get_paginator_as_context(
                ResourceObjective.objects.filter(resource=self.object).order_by("created").reverse(),
                self.request.GET,
                nb_per_page=6
            )
        )
        return context


class ResourceDetailObjectiveAddView(BasicModelDetailObjectiveAddView, ResourceDetailMixin):
    """
    Add an objective to the resource
    """

    def get_success_url(self):
        return reverse_lazy(
            "learning:resource/detail/objectives",
            kwargs={"slug": self.object.slug}
        )


class ResourceDetailObjectiveUpdateView(BasicModelDetailObjectiveUpdateView, FormView, ResourceDetailMixin):
    """
    Updating ResourceObjective
    """
    form_class = ResourceObjectiveUpdateForm


class ResourceDetailObjectiveRemoveView(BasicModelDetailObjectiveRemoveView, ResourceDetailMixin):
    """
    Removing ResourceObjective
    """


class ResourceObjectiveUpdateValidationView(ObjectObjectiveUpdateValidationView, ResourceDetailMixin):
    """
    Handle the resourceObjectiveValidation
    """
