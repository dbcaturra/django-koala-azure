#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
#
# Copyright (C) 2020 Loris Le Bris <loris.le_bris@etudiant.univ-lr.fr>
# Copyright (C) 2020 Arthur Baribeaud <arthur.baribeaud@etudiant.univ-lr.fr>
# Copyright (C) 2020 Alexis Delabarre <alexis.delabarre@etudiant.univ-lr.fr>
# Copyright (C) 2020 Célian Rolland <celian.rolland@etudiant.univ-lr.fr>
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
from typing import Type

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.forms import Form, ModelForm
from django.http import HttpResponseNotAllowed, HttpResponseNotFound, HttpRequest
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import ProcessFormView, FormView

from learning.exc import LearningError, ChangeActivityOnCourseError, UserIsAlreadyCollaborator, UserIsAlreadyAuthor, \
    UserIsAlreadyStudent
from learning.forms import CourseCreateForm, CourseUpdateFormForOwner, CourseUpdateForm, \
    ActivityCreateForm, AddStudentOnCourseForm, BasicSearchForm, \
    UserPKForm, ActivityPKForm
from learning.models import CourseCollaborator, Course, Activity, Resource, \
    CourseActivity, RegistrationOnCourse, CourseObjective, ActivityObjective, \
    ResourceObjective, get_progression_on_course_for_user, CollaboratorRole
from learning.views.helpers import PaginatorFactory, SearchQuery, InvalidFormHandlerMixin
from learning.views.includes.collaborators import BasicModelDetailCollaboratorsListView, \
    BasicModelDetailCollaboratorsAddView, BasicModelDetailCollaboratorsDeleteView, \
    BasicModelDetailCollaboratorsChangeView
from learning.views.objective import ObjectObjectiveDetailMixin, \
    BasicModelDetailObjectiveAddView, ObjectObjectiveUpdateValidationView, BasicModelDetailObjectiveRemoveView, \
    BasicModelDetailObjectiveUpdateView, CourseObjectiveUpdateForm


class CourseDetailMixin(PermissionRequiredMixin, SingleObjectMixin):
    """
    Simple Course Mixin to enrich the course detail context with boolean that indicate the role of the current
    user for instance.
    """
    model = Course
    template_name = "learning/course/detail.html"

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self) -> bool:
        return self.object.user_can_view(self.request.user)

    # noinspection PyUnresolvedReferences
    def __user_can_register(self) -> bool:
        return self.request.user != self.object.author and \
               self.request.user not in self.object.collaborators.all() and \
               self.object.can_register

    # noinspection PyUnresolvedReferences
    def __user_is_teacher(self) -> bool:
        return self.request.user == self.object.author or \
               self.request.user in self.object.collaborators.all()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_can_register"] = self.__user_can_register()

        # Add user specific elements in the context
        context["user_can_register"] = self.__user_can_register()
        context["objectives"] = PaginatorFactory.get_paginator_as_context(
            CourseObjective.objects.filter(course=self.object).order_by("created").reverse(),
            self.request.GET,
            nb_per_page=6
        )
        if self.request.user.is_authenticated:
            if self.request.user in self.object.collaborators.all():
                context["contribution"] = CourseCollaborator.objects \
                    .get(collaborator=self.request.user, course=self.object)
            registration = self.object.registrations.filter(student=self.request.user)
            context["user_is_student"] = registration.exists()
            if context.get("user_is_student", False):
                context["registration"] = registration.get()
            context["user_is_teacher"] = self.__user_is_teacher()
            context["user_is_teacher_non_editor"] = CourseCollaborator.objects.filter(
                collaborator=self.request.user, course=self.object, role=CollaboratorRole.NON_EDITOR_TEACHER.name
            ).exists()
            context["user_is_teacher_editor"] = CourseCollaborator.objects.filter(
                collaborator=self.request.user, course=self.object, role=CollaboratorRole.TEACHER.name
            ).exists()
            context["user_contribute"] = self.request.user in self.object.collaborators.all()
            context["user_is_author_of_object"] = self.request.user == self.object.author
            if self.request.user != self.object.author:
                context["auth_user"] = self.request.user
        return context


class CourseDetailView(CourseDetailMixin, PermissionRequiredMixin, DetailView):
    """
    View the detail of a course.

    .. caution:: Viewing a course requires the **view_course** permission.
    """

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to view this course."))
        return super().handle_no_permission()


class CourseCreateView(LoginRequiredMixin, InvalidFormHandlerMixin, CreateView):
    """
    View to create a new course
    """
    model = Course
    form_class = CourseCreateForm
    template_name = "learning/course/add.html"

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, _("Course “%(course)s” created.") % {"course": form.instance.name})
        return super().form_valid(form)

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        return reverse_lazy("learning:course/detail", kwargs={"slug": self.object.slug})


class CourseUpdateViewMixin(LoginRequiredMixin, CourseDetailMixin):
    """
    Mixin to update a course.

    .. caution:: Updating a course requires the **change_course** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can_change(self.request.user)

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to change this course."))
        return super().handle_no_permission()


class CourseUpdateView(CourseUpdateViewMixin, InvalidFormHandlerMixin, UpdateView):
    """
    Update a course in a HTML page. The form shown to the user depends on its role on the course. Standard editors
    will not be able to perform administration tasks (like changing privacy) whereas the owner will have this
    possibility.
    """
    form_class = CourseUpdateForm
    template_name = "learning/course/details/change.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_form_class(self) -> Type[CourseUpdateForm]:
        """
        The form class differs depending on the user has some extra rights on the object, such as changing the
        privacy value.
        :return: the corresponding CourseUpdateForm
        :rtype: CourseUpdateForm
        """
        if self.object.user_can("change_privacy", self.request.user):
            self.form_class = CourseUpdateFormForOwner
        return self.form_class

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        if form.has_changed():
            messages.success(
                self.request, _("The course “%(course)s” has been updated.") % {"course": self.object.name}
            )
        return super().form_valid(form)

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        return reverse_lazy("learning:course/detail", kwargs={"slug": self.object.slug})


class CourseDeleteViewMixin(LoginRequiredMixin, CourseDetailMixin, DeleteView):
    """
    Mixin to delete a course

    .. caution:: Deleting a course requires the **delete_course** permission.
    """

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can_delete(self.request.user)

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to delete this course."))
        super().handle_no_permission()


class CourseDeleteView(LoginRequiredMixin, CourseDetailMixin, DeleteView):
    """
    Delete a course in a HTML page.
    """
    success_url = reverse_lazy("learning:course/teaching")
    template_name = "learning/course/delete.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        messages.success(
            self.request, _("The course ”%(course)s” has been deleted") % {"course": self.object.name}
        )
        return super().get_success_url()


class CourseAsTeacherListView(LoginRequiredMixin, FormView):
    """
    List courses as a teacher. Thus, it includes courses the user manages as their author, and courses on
    which the user collaborates.
    """
    template_name = "learning/course/teaching.html"
    form_class = BasicSearchForm

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add the paginator on favourite courses of the user where he is author.
        # Prefix is “favourite”: so object are “favourite_has_obj…”
        context.update(PaginatorFactory.get_paginator_as_context(
            Course.objects.teacher_favourites_for(self.request.user),
            self.request.GET, prefix="favourite", nb_per_page=6)
        )

        # Add the paginator on courses where user is author. Prefix is “author”: so object are “author_has_obj…”
        context.update(PaginatorFactory.get_paginator_as_context(
            Course.objects.written_by(self.request.user), self.request.GET, prefix="author", nb_per_page=6)
        )

        # Add the paginator on courses where user is a collaborator. Prefix is “contributor”.
        # FIXME: this should exclude favourite courses where the user contribute
        context.update(PaginatorFactory.get_paginator_as_context(
            CourseCollaborator.objects.filter(collaborator=self.request.user), self.request.GET, prefix="contributor",
            nb_per_page=6)
        )

        # Execute the user query and add the paginator on query
        form = BasicSearchForm(data=self.request.GET)
        if form.is_valid() and form.cleaned_data.get("query", str()):
            context.update(PaginatorFactory.get_paginator_as_context(Course.objects.taught_by(
                self.request.user, query=form.cleaned_data.get("query", str())
            ).all(), self.request.GET, prefix="search"))

        # Add the query form in the view
        context["form"] = form
        return context


class CourseAsStudentListView(LoginRequiredMixin, FormView):
    """
    List courses on which the user is registered has a student
    """
    template_name = "learning/course/student.html"
    form_class = BasicSearchForm

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add the paginator on favourite courses of the user where he is student.
        # Prefix is “favourite”: so object are “favourite_has_obj…”
        context.update(PaginatorFactory.get_paginator_as_context(
            Course.objects.student_favourites_for(self.request.user),
            self.request.GET, prefix="favourite", nb_per_page=6)
        )

        # Add the paginator on courses where user is student. Prefix is “follow”: so object are “follow_has_obj…”
        context.update(PaginatorFactory.get_paginator_as_context(
            Course.objects.followed_by_without_favorites(self.request.user),
            self.request.GET, prefix="follow", nb_per_page=6)
        )

        # Execute the user query and add the paginator on query
        form = BasicSearchForm(data=self.request.GET)
        if form.is_valid() and form.cleaned_data.get("query", str()):
            context.update(PaginatorFactory.get_paginator_as_context(Course.objects.followed_by(
                self.request.user, query=form.cleaned_data.get("query", str())
            ).all(), self.request.GET, prefix="search"))

        # Add the query form in the view
        context["form"] = form
        return context


class CourseFavouriteAsStudentListView(CourseAsStudentListView, InvalidFormHandlerMixin, ProcessFormView):

    def post(self, request, *args, **kwargs):
        student = self.request.user
        course = get_object_or_404(Course, slug=kwargs.get("course_slug", None))
        if student in course.favourite_for.all():
            course.favourite_for.remove(student)
            messages.success(
                self.request,
                _("%(course)s has been removed from your favourites courses.")
                % {"course": course.name}
            )
        else:
            course.favourite_for.add(student)
            messages.success(
                self.request,
                _("%(course)s has been added to your favourites courses.")
                % {"course": course.name}
            )
        return redirect("learning:course/my")


class CourseFavouriteAsTeacherListView(CourseAsTeacherListView, InvalidFormHandlerMixin, ProcessFormView):

    def post(self, request, *args, **kwargs):
        teacher = self.request.user
        course = get_object_or_404(Course, slug=kwargs.get("course_slug", None))
        if teacher in course.favourite_for.all():
            course.favourite_for.remove(teacher)
            messages.success(
                self.request,
                _("%(course)s has been removed from your favourites courses.")
                % {"course": course.name}
            )
        else:
            course.favourite_for.add(teacher)
            messages.success(
                self.request,
                _("%(course)s has been added to your favourites courses.")
                % {"course": course.name}
            )
        return redirect("learning:course/teaching")


class CourseDetailActivitiesView(CourseDetailView):
    """
    View activities presented for students. This is a paginator for which a page contains only one activity.
    """
    template_name = "learning/course/details/activities.html"

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.course_activities.count() > 0:
            return super().dispatch(request, *args, **kwargs)
        messages.warning(request, _("This course does not have any activity yet."))
        return redirect("learning:course/detail", slug=self.object.slug)

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add the current course activity into the context
        if "activity_slug" in self.kwargs.keys():
            course_activity = get_object_or_404(
                CourseActivity, activity__slug=self.kwargs.get("activity_slug"), course=self.object
            )
        else:
            course_activity = self.object.course_activities.first()
        context["current_course_activity"] = course_activity
        context["current_course_activity_objective"] = PaginatorFactory.get_paginator_as_context(
            ActivityObjective.objects.filter(activity=course_activity.activity).order_by("created").reverse(),
            self.request.GET,
            nb_per_page=6
        )
        if self.request.user != self.object.author:
            context["auth_user"] = self.request.user

        # Add previous and next activities in the context
        context["next_course_activity"] = CourseActivity.objects.filter(
            course=self.object, rank=course_activity.rank + 1
        ).first()
        context["previous_course_activity"] = CourseActivity.objects.filter(
            course=self.object, rank=course_activity.rank - 1
        ).first()
        return context


class CourseDetailActivityResourceView(CourseDetailView):
    """
    View a specific resource on an activity.
    """
    template_name = "learning/course/details/activity_resource.html"

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.activity = get_object_or_404(Activity, slug=self.kwargs.get("activity_slug"))
        self.resource = get_object_or_404(Resource, slug=self.kwargs.get("resource_slug"))
        if self.object.course_activities.filter(activity=self.activity).exists() and \
            self.activity.resources.filter(id=self.resource.id).exists():
            return self.get(request, args, kwargs)
        return HttpResponseNotFound()

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["activity"] = self.activity
        context["resource"] = self.resource
        context["activity"] = self.activity
        context["resource"] = self.resource
        context["current_course_activity_resource_objective"] = PaginatorFactory.get_paginator_as_context(
            ResourceObjective.objects.filter(resource=self.resource).order_by("created").reverse(),
            self.request.GET,
            nb_per_page=6
        )
        return context


class CourseDetailCollaboratorsListView(BasicModelDetailCollaboratorsListView, CourseDetailMixin):
    """
    View collaborators on a course in a HTML page.
    """
    template_name = "learning/course/details/collaborators.html"


class CourseDetailCollaboratorsAddView(BasicModelDetailCollaboratorsAddView, CourseDetailMixin):
    """
    Add a collaborator on a course in a HTML page.
    """
    success_url = "learning:course/detail/collaborators"


class CourseDetailCollaboratorsChangeView(BasicModelDetailCollaboratorsChangeView, CourseDetailMixin):
    """
    Change a collaborator on a course in a HTML page.
    """
    success_url = "learning:course/detail/collaborators"


class CourseDetailCollaboratorsDeleteView(BasicModelDetailCollaboratorsDeleteView, CourseDetailMixin):
    """
    Delete a collaborator from a course in a HTML page.
    """
    success_url = "learning:course/detail/collaborators"


class CourseDetailStudentViewMixin(LoginRequiredMixin, CourseDetailView):
    """
    Mixin to view students registered on a course.

    .. note:: Viewing students registered on a course requires the **view_students** permission.
    """

    # noinspection PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("view_students", self.request.user) and super().has_permission()

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to view students of this course."))
        return super().handle_no_permission()


class CourseDetailStudentsView(CourseDetailStudentViewMixin, FormView):
    """
    View students registered on a course in a HTML page.
    """
    form_class = AddStudentOnCourseForm
    template_name = "learning/course/details/students.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            PaginatorFactory.get_paginator_as_context(
                self.object.registrations.order_by("student__last_login").all(),
                self.request.GET, nb_per_page=10)
        )
        context["number_student"] = self.object.registrations.count()
        return context


class CourseDetailStudentsAddViewMixin(LoginRequiredMixin, CourseDetailMixin):
    """
    Mixin to register a student on a course.

    .. note:: Adding a student on a course requires the **add_student** permission..
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("add_student", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to add a student on this course."))
        return super().handle_no_permission()


class CourseDetailStudentsAddView(CourseDetailStudentsAddViewMixin, InvalidFormHandlerMixin, FormView):
    """
    Register a student on a course in a HTML page.
    """
    form_class = AddStudentOnCourseForm

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def form_valid(self, form):
        self.object = self.get_object()
        username = form.cleaned_data.get("username", None)
        locked = form.cleaned_data.get("registration_locked", True)
        try:
            user = get_user_model().objects.filter(username=username).get()
            self.object.register_student(user, locked)
            messages.success(self.request, _("%(user)s is now registered on this course.") % {"user": user})
        except ObjectDoesNotExist:
            messages.error(self.request, _("This user does not exists."))
        except (UserIsAlreadyStudent, UserIsAlreadyCollaborator, UserIsAlreadyAuthor) as ex:
            messages.warning(self.request, ex)
        except LearningError as ex:
            messages.error(self.request, ex)
        return redirect("learning:course/detail/students", slug=self.object.slug)

    # noinspection PyMissingOrEmptyDocstring
    def form_invalid(self, form):
        super().form_invalid(form)
        return redirect("learning:course/detail/students", slug=self.object.slug)


class CourseDetailStudentChangeViewMixin(LoginRequiredMixin, CourseDetailMixin):
    """
    Mixin to change a student on a course

    .. caution:: Changing a student on a course requires the **change_student** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("change_student", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(self.request, _("You do not have the required permissions to change a student on this course."))
        return super().handle_no_permission()


class CourseDetailStudentChangeView(CourseDetailStudentChangeViewMixin, InvalidFormHandlerMixin, ProcessFormView):
    """
    Change a student on a course in a HTML page.
    """

    # noinspection PyMissingOrEmptyDocstring
    class RegistrationPKForm(Form):
        """
        The registration form that is used to track the student id.
        """
        registration_pk = forms.IntegerField(min_value=1, required=True)

    def post(self, request, *args, **kwargs):
        registration_pk_form = self.RegistrationPKForm(kwargs or None)
        if registration_pk_form.is_valid():
            registration = get_object_or_404(
                RegistrationOnCourse, pk=registration_pk_form.cleaned_data.get("registration_pk")
            )
            registration.registration_locked = not registration.registration_locked
            registration.save()
            if registration.registration_locked:
                messages.success(
                    self.request,
                    _("Registration is now locked for %(user)s. This user will not be able to unregister.")
                    % {"user": registration.student}
                )
                return redirect("learning:course/detail/students", slug=self.object.slug)
            messages.success(
                self.request,
                _("%(user)s now can unregister by itself from this course.")
                % {"user": registration.student}
            )
            return redirect("learning:course/detail/students", slug=self.object.slug)
        return HttpResponseNotFound(_("The given registration primary key is invalid. It this intentional?"))


class CourseDetailStudentsDeleteViewMixin(LoginRequiredMixin, CourseDetailMixin):
    """
    Mixin to unregister a student on a course

    .. caution:: Unregistering a student on a course requires the **delete_student** permission.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("delete_student", self.request.user) and super().has_permission()

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request, _("You do not have the required permissions to unregister a student from this course.")
        )
        return super().handle_no_permission()


class CourseDetailStudentsDeleteView(CourseDetailStudentsDeleteViewMixin, ProcessFormView):
    """
    Unregister a student from a course.
    """

    # noinspection PyMissingOrEmptyDocstring
    def post(self, request, *args, **kwargs):
        user_pk_form = UserPKForm(self.request.POST or None)
        if user_pk_form.is_valid():
            student = get_object_or_404(get_user_model(), pk=user_pk_form.cleaned_data.get("user_pk"))
            self.object.unsubscribe_student(student)
            messages.success(
                self.request,
                _("The student “%(student)s” has been unregistered from the course “%(course)s”.")
                % {"course": self.object, "student": student}
            )
            return redirect("learning:course/detail/students", slug=self.object.slug)
        return HttpResponseNotFound(user_pk_form.errors.get("user_pk"))

    # noinspection PyMissingOrEmptyDocstring
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class CourseDetailSimilarViewMixin(LoginRequiredMixin, CourseDetailView):
    """
    Mixin to view courses that are similar to the current one.

    .. caution:: Viewing similar courses requires the **view_similar** permission.
    """

    # noinspection PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can("view_similar", self.request.user) and super().has_permission()

    # noinspection PyMissingOrEmptyDocstring
    def handle_no_permission(self):  # pragma: no cover
        messages.error(self.request, _("You do not have the required permissions to view similar courses."))
        return super().handle_no_permission()


class CourseDetailSimilarView(CourseDetailSimilarViewMixin):
    """
    View courses that are similar to the current one.

    .. note:: This requires the permission to view similar courses and to view the course itself.
    """
    template_name = "learning/course/details/similar.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # noinspection PyBroadException
        try:
            similar_list = [
                similar for similar in self.object.tags.similar_objects()
                if isinstance(similar, Course) and similar.user_can_view(self.request.user)
            ]
            context.update(PaginatorFactory.get_paginator_as_context(similar_list, self.request.GET, nb_per_page=9))
        # django-taggit similar tags can have weird behaviour sometimes: https://github.com/jazzband/django-taggit/issues/80
        except Exception:
            messages.error(
                self.request,
                _("We’re having some problems finding similar courses… We try to fix this as soon as possible.")
            )
        return context


class CourseRegisterView(LoginRequiredMixin, CourseDetailView, ProcessFormView):
    """
    Register the current user on the course.
    """

    # noinspection PyUnusedLocal,PyMissingOrEmptyDocstring
    def post(self, request, *args, **kwargs):
        try:
            self.object.register(request.user)
            messages.success(
                request, _("You have been registered on the course “%(course)s”") % {"course": self.object}
            )
        except LearningError as ex:
            messages.error(request, ex)
        return redirect("learning:course/detail", slug=self.object.slug)

    # noinspection PyMissingOrEmptyDocstring
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class CourseUnregisterView(LoginRequiredMixin, CourseDetailView, FormView):
    """
    Unsubscribe the current user from the course.
    """

    # noinspection PyUnusedLocal,PyMissingOrEmptyDocstring
    def post(self, request, *args, **kwargs):
        try:
            self.object.unsubscribe(request.user)
            messages.success(
                request, _("You have been unregistered from the course “%(course)s”") % {"course": self.object}
            )
        except LearningError as ex:
            messages.error(request, ex)
        return redirect("learning:course/detail", slug=self.object.slug)

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


class CourseSearchView(TemplateView):
    """
    Search for a specific course.
    """
    template_name = "learning/course/search.html"

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Show the user some recommended courses, based on its profile
        queryset = None
        if self.request.user.is_authenticated:
            queryset = Course.objects.recommendations_for(self.request.user).all()
        context.update(PaginatorFactory.get_paginator_as_context(
            queryset, self.request.GET, prefix="recommended", nb_per_page=9)
        )

        # Show the user all public courses
        context.update(PaginatorFactory.get_paginator_as_context(
            Course.objects.public_without_followed_by_without_taught_by(self.request.user, self.request.user).all(),
            self.request.GET, prefix="public", nb_per_page=33)
        )

        # The search results
        context.update(SearchQuery.search_query_as_context(Course, self.request.GET))
        return context


class ActivityCreateOnCourseViewMixin(LoginRequiredMixin, CourseDetailMixin):
    """
    Mixin to create an activity on a course.

    .. caution:: Adding an activity on a course implies you have the **change** permission and it’s not read-only.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def has_permission(self):
        return self.object.user_can_change(self.request.user) and not self.object.read_only

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You do not have the required permissions to change this course. "
              "It may be read-only because archived or you may not have the rights to edit the course.")
        )
        return super().handle_no_permission()


class ActivityAttachOnCourseViewMixin(ActivityCreateOnCourseViewMixin):
    """
    Mixin to attach an activity on a course.

    .. caution:: Adding an activity on a course implies you have the **change** permission and it’s not read-only.
    """

    # noinspection PyUnresolvedReferences,PyMissingOrEmptyDocstring
    def handle_no_permission(self):
        messages.warning(
            self.request, _("You do not have the required permission to add an activity on this course.")
        )
        return super().handle_no_permission()


class ActivityCreateOnCourseView(ActivityCreateOnCourseViewMixin, InvalidFormHandlerMixin, UpdateView):
    """
    View to create a new activity and automatically link it with the current course.

    .. note:: This requires the right to change the course, and implies the course is not read-only (can be edited)
    .. note:: This implies that data from the CourseActivity and Activity models are presented in two separated forms.
    """
    template_name = "learning/course/details/add_activity_on_course.html"

    # noinspection PyMissingOrEmptyDocstring
    # FIXME: is this really necessary? It should be handled by Django itself.
    def get_form(self, form_class=None) -> ModelForm:
        return ActivityCreateForm(self.request.POST or None)

    # noinspection PyMissingOrEmptyDocstring
    def form_valid(self, form):
        activity = form.instance  # Extract form instances
        activity.author = self.request.user  # Manually set the activity author to the current user
        try:
            self.object.add_activity(activity)
            messages.success(
                self.request,
                _("The activity “%(activity)s” has been added to the course “%(course)s”.")
                % {"activity": activity.name, "course": self.object.name}
            )
            return super().form_valid(form)
        except LearningError as ex:
            messages.error(self.request, ex)
            return self.form_invalid(form)

    # noinspection PyMissingOrEmptyDocstring
    def form_invalid(self, form):
        super().form_invalid(form)
        context = super().get_context_data()
        context.update({"course": self.object, "form": self.get_form()})
        return render(self.request, self.template_name, context)

    # noinspection PyMissingOrEmptyDocstring
    def get_success_url(self):
        return reverse_lazy("learning:activity/detail", kwargs={"slug": self.object.slug})


class ActivityAttachOnCourseView(ActivityAttachOnCourseViewMixin, FormView):
    """
    Attach an activity on an existing course.
    """
    template_name = "learning/course/details/attach_activity.html"
    form_class = BasicSearchForm

    # noinspection PyMissingOrEmptyDocstring
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # All available activities for new activities
        context.update(PaginatorFactory.get_paginator_as_context(
            Activity.objects.reusable(self.object, self.request.user),
            self.request.GET, prefix="reusable", nb_per_page=6)
        )

        # User may query some words using the search filter
        form = BasicSearchForm(data=self.request.GET)
        if form.is_valid() and form.cleaned_data.get("query", str()):
            query = form.cleaned_data.get("query", str())
            context.update(PaginatorFactory.get_paginator_as_context(
                Activity.objects.reusable(self.object, self.request.user, query=query),
                self.request.GET, prefix="search", nb_per_page=6)
            )

        # Add the query form in the view
        context["form"] = form
        return context

    # noinspection PyAttributeOutsideInit,PyMissingOrEmptyDocstring
    def post(self, request, *args, **kwargs):
        activity_pk_form = ActivityPKForm(self.request.POST or None)
        if activity_pk_form.is_valid():
            activity = get_object_or_404(Activity, pk=activity_pk_form.cleaned_data.get("activity"))
            try:
                self.object.add_activity(activity)
                messages.success(
                    self.request,
                    _("Activity “%(activity)s” added to the course “%(course)s”")
                    % {"activity": activity, "course": self.object}
                )
            except LearningError as ex:
                messages.error(self.request, ex)
            return redirect("learning:course/detail/activity/attach", slug=self.object.slug)
        return HttpResponseNotFound(activity_pk_form.errors.get("activity"))


@login_required
@require_http_methods(["POST"])
def activity_on_course_up_view(request: HttpRequest, slug: str):
    """
    Increase by 1 point the rank of the activity on the course.

    .. caution:: Changing the order or activities in a course requires the **change_course** permission.
    .. important:: The activity to change is given as a POST parameter called **activity** and contains the resource
    primary key.

    :param request: django request object
    :type request: django.http.HttpRequest
    :param slug: course slug
    :type slug: str
    :return: the course detail view
    """

    # Retrieve objects : course, activity, the current course activity
    course = get_object_or_404(Course, slug=slug)

    if course.user_can_change(request.user):
        activity_pk_form = ActivityPKForm(request.POST or None)
        if activity_pk_form.is_valid():
            activity = get_object_or_404(Activity, pk=activity_pk_form.cleaned_data.get("activity"))
            course_activity = get_object_or_404(CourseActivity, course=course, activity=activity)
            previous_course_activity = get_object_or_404(
                CourseActivity, course=course, rank=course_activity.rank - 1
            )

            # Switch course activity ranks
            course_activity.rank = previous_course_activity.rank
            previous_course_activity.rank += 1

            # Save objects
            course_activity.save()
            previous_course_activity.save()

            messages.success(
                request,
                _("Activity “%(activity)s” was repositioned and is now the activity n°%(rank)d on this course.")
                % {"activity": activity, "rank": course_activity.rank}
            )
            return redirect("learning:course/detail", slug=course.slug)
        return HttpResponseNotFound(activity_pk_form.errors.get("activity"))

    # User cannot change the course
    messages.error(request, _("You do not have the required permission to change activities of this course."))
    raise PermissionDenied()


# noinspection PyUnresolvedReferences
@login_required
@require_http_methods(["POST"])
def activity_on_course_unlink_view(request: HttpRequest, slug: str):
    """
    Unlink an activity from a course. This means the activity will no longer be attached to the course. The activity
    is not removed.

    .. caution:: Changing the activities in a course requires the **change_course** permission.
    .. important:: The activity to change is given as a POST parameter called **activity** and contains the resource primary key.

    :param request: django request object
    :type request: django.http.HttpRequest
    :param slug: course slug
    :type slug: str
    :return: the course detail view
    """
    course = get_object_or_404(Course, slug=slug)
    if course.user_can_change(request.user):
        activity_pk_form = ActivityPKForm(request.POST or None)
        if activity_pk_form.is_valid():
            activity = get_object_or_404(Activity, pk=activity_pk_form.cleaned_data.get("activity"))
            try:
                course.remove_activity(activity)
                messages.success(request, _("The activity “%(activity)s” has been removed from this course. "
                                            "The activity itself has not been removed.") % {"activity": activity})
            except ChangeActivityOnCourseError as ex:
                messages.error(request, ex)
            return redirect("learning:course/detail", slug=course.slug)
        return HttpResponseNotFound(activity_pk_form.errors.get("activity"))

    # Not permission to change the course
    messages.error(
        request,
        _("You do not have the required permissions to unlink this activity from this course.")
    )
    raise PermissionDenied()


# noinspection PyUnresolvedReferences
@login_required
@require_http_methods(["POST"])
def activity_on_course_delete_view(request: HttpRequest, slug: str):
    """
    Delete an activity which is currently attached to a course. The link between the activity and the course
    will be removed, as well as the activity itself.

    .. caution:: Changing the activities in a course requires the **change_course** permission.
    .. important:: The activity to change is given as a POST parameter called **activity** and contains the resource
    primary key.

    :param request: django request object
    :type request: django.http.HttpRequest
    :param slug: course slug
    :type slug: str
    :return: the course detail view
    """
    course = get_object_or_404(Course, slug=slug)
    activity_pk_form = ActivityPKForm(request.POST or None)
    if activity_pk_form.is_valid():
        activity = get_object_or_404(Activity, pk=activity_pk_form.cleaned_data.get("activity"))
        if course.user_can_change(request.user) and activity.user_can_delete(request.user):
            try:
                course.remove_activity(activity)
                activity.delete()
                messages.success(request, _("The activity “%(activity)s” has been removed from this course. "
                                            "The activity has also been removed.") % {"activity": activity})
            except ChangeActivityOnCourseError as ex:
                messages.error(request, ex)
            return redirect("learning:course/detail", slug=course.slug)
        # Not permission to change delete the activity
        messages.error(request, _("You do not have the required permissions to delete this activity."))
        raise PermissionDenied()
    return HttpResponseNotFound(activity_pk_form.errors.get("activity"))


class CourseDetailObjectiveListView(ObjectObjectiveDetailMixin, CourseDetailView):
    template_name = "learning/course/details/objective.html"
    """
    Lists the objectives in Course
    User can add objective from here
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(
            PaginatorFactory.get_paginator_as_context(
                CourseObjective.objects.filter(course=self.object).order_by("created").reverse(),
                self.request.GET,
                nb_per_page=6
            )
        )
        if self.request.user.is_authenticated:
            if self.request.user != self.object.author:
                context["auth_user"] = self.request.user
        return context


class CourseDetailObjectiveAddView(BasicModelDetailObjectiveAddView, CourseDetailMixin):
    """
    The view that add the objective in the course
    """

    def get_success_url(self):
        return reverse_lazy("learning:course/detail/objectives", kwargs={"slug": self.object.slug})


class CourseDetailObjectiveUpdateView(BasicModelDetailObjectiveUpdateView, FormView, CourseDetailMixin):
    """
    Updating CourseObjective
    """
    form_class = CourseObjectiveUpdateForm


class CourseDetailObjectiveRemoveView(BasicModelDetailObjectiveRemoveView, CourseDetailMixin):
    """
    Removing CourseObjective
    """


class CourseObjectiveUpdateValidationView(ObjectObjectiveUpdateValidationView, CourseDetailMixin):
    """
    Handle the CourseObjectiveValidation
    """


class StudentCourseProgressionMixin(CourseDetailMixin, LoginRequiredMixin, DetailView):
    """
    The progression of a student from the student
    """
    template_name = "learning/course/details/progression.html"

    def handle_no_permission(self):
        messages.info(self.request, _("You need to logging if you want to follow you progression"))
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(get_progression_on_course_for_user(self.object, self.request.user))
        return context


class TeacherCourseProgressionMixin(CourseDetailMixin, LoginRequiredMixin, DetailView):
    """
    The progression of a student from an teacher
    """
    template_name = "learning/course/details/progression.html"

    def has_permission(self) -> bool:
        return self.request.user == self.object.author or self.request.user in self.object.collaborators.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        if "username_id" in self.kwargs:
            context["student"] = get_object_or_404(get_user_model(), pk=self.kwargs.get("username_id", None))
            context.update(get_progression_on_course_for_user(self.object, context.get("student")))
        return context
