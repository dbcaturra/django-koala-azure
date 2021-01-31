#
# Copyright (C) 2020 Louis Barbier <louis.barbier41@outlook.fr>
# Copyright (C) 2020 Guillaume Bernard <contact@guillaume-bernard.fr>
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
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.forms import Form
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, TemplateView, FormView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from learning.exc import ObjectiveAlreadyInModel, ObjectiveAlreadyExists
from learning.forms import ObjectiveCreateForm, AddObjectiveForm, CourseObjectiveUpdateForm, \
    ActivityObjectiveUpdateForm, ResourceObjectiveUpdateForm
from learning.models import Objective, Course, Resource, Activity
from learning.views.helpers import InvalidFormHandlerMixin, PaginatorFactory


class ObjectiveCreateView(LoginRequiredMixin, InvalidFormHandlerMixin, CreateView):
    """
    The view that allows user to create Objective
    """
    model = Objective
    form_class = ObjectiveCreateForm
    template_name = "learning/taxonomy/objective/create.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, _("Objective added: “%(objective)s”") % {"objective": form.instance.ability})
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("learning:objective/create")


class ObjectiveDeleteView(LoginRequiredMixin, InvalidFormHandlerMixin, FormView):
    class ObjectivePKForm(Form):
        objective_pk = forms.IntegerField(min_value=1, required=True)

    def post(self, request, *args, **kwargs):
        objective_pk_form = self.ObjectivePKForm(self.request.POST or None)
        if objective_pk_form.is_valid():
            self.object = get_object_or_404(
                Objective, pk=objective_pk_form.cleaned_data.get("objective_pk", None)
            )
            self.form_valid(objective_pk_form)
        return redirect(request.META.get("HTTP_REFERER", "learning:objective"))

    def form_valid(self, form):
        if self.request.user == self.object.author:
            messages.success(
                self.request, _("The objective “%(objective)s” has been deleted") % {"objective": self.object.ability}
            )
            self.object.delete()
        else:
            self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("You don’t have the permission to delete this objective"))
        raise PermissionDenied()


class ObjectiveListView(TemplateView):
    """
    The view that allows the user to list objective
    """
    model = Objective
    template_name = "learning/taxonomy/objective/my_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        if self.request.user.is_authenticated:
            # here the objective that user gained first
            context.update(
                PaginatorFactory.get_paginator_as_context(
                    Objective.objects.all().order_by("created"),
                    self.request.GET,
                    nb_per_page=6
                )
            )
        else:
            # here all the objectives
            context.update(
                PaginatorFactory.get_paginator_as_context(
                    Objective.objects.all().order_by("created"),
                    self.request.GET,
                    nb_per_page=6
                )
            )
        return context


class ObjectiveDetailMixin(SingleObjectMixin):
    model = Objective
    template_name = "learning/taxonomy/objective/detail/detail.html"


class ObjectiveDetailView(ObjectiveDetailMixin, DetailView):
    """
    This view shows the details of an objective
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(
            PaginatorFactory.get_paginator_as_context(
                [course for course in Course.objects.all() if self.object in course.get_all_objectives()],
                self.request.GET,
                nb_per_page=6
            )
        )
        return context


class BasicModelDetailObjectiveAddMixin(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin):
    """
    This is the class that manage the permissions for the objective addition
    """

    # noinspection PyAttributeOutsideInit
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyUnresolvedReferences
    def has_permission(self):
        return self.object.user_can("add_objective", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to add an objective on this %(object)s.")
            % {"object": _(self.object.__class__.__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailObjectiveAddView(BasicModelDetailObjectiveAddMixin, InvalidFormHandlerMixin, FormView):
    """
    This is the view that manage the permissions for the objective addition
    """

    form_class = AddObjectiveForm

    def get_form(self, form_class=None):
        form = super().get_form()
        result = Objective.objects.most_relevant_objective_for_model(self.get_object())
        if result.count() > 0:
            form.fields["existing_ability"].choices = \
                [("", _("Recommended objective exists but I create my own new objective"))] \
                + [(choice.id, choice.ability) for choice in result.all()]
        return form

    def form_valid(self, form):
        model_object = self.get_object()
        ability = form.cleaned_data.get("ability", None)
        taxonomy_level = form.cleaned_data.get("taxonomy_level", None)
        objective_reusable = form.cleaned_data.get("objective_reusable", None)
        existing_ability = form.cleaned_data.get("existing_ability", None)
        objective = None
        if existing_ability == str():
            try:
                objective = Objective.objects.create(
                    ability=ability, language=model_object.language, author=self.request.user
                )
            except ObjectiveAlreadyExists:
                objective = Objective.objects.filter(ability=ability, language=model_object.language).get()
        else:
            try:
                objective = Objective.objects.filter(pk=existing_ability).get()
            except objective.DoesNotExist:
                messages.error(self.request,
                               _("This objective “%(objective)s” does not exist") % {"objective": ability})
                return super().form_invalid(form)

        try:
            model_object.add_objective(
                objective=objective, taxonomy_level=taxonomy_level, objective_reusable=objective_reusable
            )
        except ObjectiveAlreadyInModel:
            messages.error(
                self.request,
                _("This objective %(objective)s is already in %(obj_type)s")
                % {"objective": ability, "obj_type": model_object.name})
            return super().form_invalid(form)

        messages.success(self.request, _("Objective added with success"))
        return super().form_valid(form)


class BasicModelDetailObjectiveRemoveMixin(PermissionRequiredMixin, LoginRequiredMixin):
    """
    This is the class that manage the permissions for the objective addition
    """

    # noinspection PyAttributeOutsideInit
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyUnresolvedReferences
    def has_permission(self):
        return self.object.user_can("delete_objective", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to remove an objective on this %(object)s.")
            % {"object": _(type(self.object).__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailObjectiveRemoveView(BasicModelDetailObjectiveRemoveMixin, InvalidFormHandlerMixin, FormView):
    class ObjectivePKForm(Form):
        objective_pk = forms.IntegerField(min_value=1, required=True)

    form_class = ObjectivePKForm

    def post(self, request, *args, **kwargs):
        objective_pk_form = self.ObjectivePKForm(self.request.POST or None)
        if objective_pk_form.is_valid():
            objective = get_object_or_404(self.object.object_objectives,
                                          pk=objective_pk_form.cleaned_data.get("objective_pk", None))
            self.object.remove_objective(objective.objective)
            messages.success(
                self.request,
                _("You successfully removed the objective “%(objective_ability)s“ from %(object)s")
                % {"object": self.object.name, "objective_ability": objective.objective.ability})
        else:
            messages.error(self.request, _("You have entered a wrong primary key"))
        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse_lazy(
                    "learning:%(object)s/detail/objectives" % {"object": type(self.object).__name__.lower()},
                    kwargs={"slug": self.object.slug}
                )
            )
        )

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class BasicModelDetailObjectiveUpdateMixin(PermissionRequiredMixin, LoginRequiredMixin):
    """
    This is the class that manage the permissions for the objective addition
    """

    # noinspection PyAttributeOutsideInit
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyUnresolvedReferences
    def has_permission(self):
        return self.object.user_can("add_objective", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to change an objective on this %(object)s.")
            % {"object": _(type(self.object).__name__.lower())}
        )
        return super().handle_no_permission()


class BasicModelDetailObjectiveUpdateView(BasicModelDetailObjectiveUpdateMixin, InvalidFormHandlerMixin,
                                          UpdateView):
    """
    Change a objective on a course/activity/resource in a HTML page.
    """

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    class ObjectivePKForm(Form):
        objective_pk = forms.IntegerField(min_value=1, required=True)

    def get_form_depending_on_object(self):
        form = None
        if isinstance(self.object, Course):
            form = CourseObjectiveUpdateForm
        elif isinstance(self.object, Activity):
            form = ActivityObjectiveUpdateForm
        elif isinstance(self.object, Resource):
            form = ResourceObjectiveUpdateForm
        return form

    def post(self, request, *args, **kwargs):
        objective_pk_form = self.ObjectivePKForm(self.request.POST or None)
        if objective_pk_form.is_valid():
            self.object_objective = get_object_or_404(self.object.object_objectives,
                                                      pk=objective_pk_form.cleaned_data.get("objective_pk", None))

            form = self.get_form_depending_on_object()(request.POST,
                                                       instance=self.object_objective,
                                                       initial={"ability": self.object_objective.objective.ability})
            if form.is_valid():
                self.form_valid(form)
                messages.success(self.request, _("You have successfully updated the objective "))
            else:
                messages.error(self.request, _("An error has occurred in the modification of objective "))

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse_lazy(
                    "learning:%(object)s/detail/objectives" % {"object": type(self.object).__name__.lower()},
                    kwargs={"slug": self.object.slug}
                )
            )
        )

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])

    def form_valid(self, form):
        changed_object = form.save(commit=False)
        self.object_objective.taxonomy_level = changed_object.taxonomy_level
        self.object_objective.objective_reusable = changed_object.objective_reusable
        if self.request.user == self.object_objective.objective.author:
            if self.object_objective.objective.ability != form.cleaned_data.get("ability", None):
                self.object_objective.objective.ability = form.cleaned_data.get("ability", None)
                self.object_objective.objective.save()
        self.object_objective.save()


class ObjectObjectiveDetailMixin(SingleObjectMixin):
    """
    Information for the creation of EntityObjective
    """


####################################
# Adding an student to validators #
###################################


class ObjectiveUpdateValidationMixin(LoginRequiredMixin, PermissionRequiredMixin, FormView):

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyUnresolvedReferences
    def has_permission(self):
        return self.object.user_can_view(self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to validate an objective on this %(object)s.")
            % {"object": _(type(self.object).__name__.lower())}
        )
        return super().handle_no_permission()


class ObjectObjectiveUpdateValidationView(InvalidFormHandlerMixin, ObjectiveUpdateValidationMixin):
    """
    Update the validation on ObjectObjective
    todo: Update the field validated_the of EntityObjective
    """

    class ValidationObjectivePKForm(Form):
        pk_object_objective = forms.IntegerField(min_value=1, required=True)

    form_class = ValidationObjectivePKForm

    def post(self, request, *args, **kwargs):
        # Validate the EntityObjective
        objective_pk_form = self.ValidationObjectivePKForm(self.request.POST or None)
        if objective_pk_form.is_valid():
            objective = get_object_or_404(
                self.object.object_objectives,
                pk=objective_pk_form.cleaned_data.get("pk_object_objective", None)
            )
            if self.request.user in objective.validators.all():
                objective.change_validation(self.request.user)
                messages.info(
                    self.request,
                    _("You have successfully disclaimed the objective “%(objective)s”")
                    % {"objective": objective.objective.ability}
                )
            else:
                objective.change_validation(self.request.user)
                messages.success(
                    self.request,
                    _("You have successfully validated the objective “%(objective)s”")
                    % {"objective": objective.objective.ability}
                )

        else:
            messages.error(self.request, _("You have entered a wrong primary key"))

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse_lazy(
                    "learning:%(object)s/detail/objectives" % {"object": type(self.object).__name__.lower()},
                    kwargs={"slug": self.object.slug}
                )
            )
        )

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
