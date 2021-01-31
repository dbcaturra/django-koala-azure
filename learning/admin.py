#
# Copyright (C) 2019-2020 Guillaume Bernard <guillaume.bernard@koala-lms.org>
#
# Copyright (C) 2020 Loris Le Bris <loris.le_bris@etudiant.univ-lr.fr>
# Copyright (C) 2020 Arthur Baribeaud <arthur.baribeaud@etudiant.univ-lr.fr>
# Copyright (C) 2020 Alexis Delabarre <alexis.delabarre@etudiant.univ-lr.fr>
# Copyright (C) 2020 Célian Rolland <celian.rolland@etudiant.univ-lr.fr>
#
# Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
# Copyright (C) 2020 Dervin Enard <dervin@hotmail.fr>
# Copyright (C) 2020 Olivia Bove <olivia.bove@hotmail.fr>
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

from django.contrib import admin
from django.contrib.admin import TabularInline, ModelAdmin

from learning.forms import CourseUpdateAdminForm, ActivityAdminUpdateForm, ResourceAdminUpdateForm, \
    ObjectiveAdminCreateForm, \
    ActivityObjectiveAdminCreateForm, CourseObjectiveAdminCreateForm, ResourceObjectiveAdminCreateForm
from learning.models import Course, Activity, CourseActivity, CourseCollaborator, Resource, RegistrationOnCourse, \
    ActivityCollaborator, ResourceCollaborator, CourseObjective, ActivityObjective, ResourceObjective, Objective


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    """
     Inheriting from GuardedModelAdmin just adds access to per-object
     permission management tools. This can be replaced by ModelAdmin at any
     time.
    """

    class CourseActivityInline(TabularInline):
        model = CourseActivity
        extra = 0

    class CourseCollaboratorsInline(TabularInline):
        model = CourseCollaborator
        readonly_fields = ("created", "updated",)
        extra = 0

    class RegistrationOnCourseInline(TabularInline):
        model = RegistrationOnCourse
        readonly_fields = ("created", "updated", "self_registration")
        extra = 0

    class ObjectiveOnCourseInline(TabularInline):
        model = CourseObjective
        readonly_fields = ('taxonomy_level', 'objective', 'objective_reusable', 'created')
        extra = 0

    form = CourseUpdateAdminForm
    list_display = ("id", "name", "state", "author", "published", "updated")
    list_display_links = ("id", "name")
    list_filter = ("published", "state")
    readonly_fields = ("slug",)

    inlines = [
        RegistrationOnCourseInline,
        CourseCollaboratorsInline,
        CourseActivityInline,
        ObjectiveOnCourseInline,
    ]

    def save_formset(self, request, form, formset, change):
        super(CourseAdmin, self).save_formset(request, form, formset, change)
        # When CourseActivity objects are added, they may not be in proper order, or with gaps
        # between ranks. Calling save again will ensure they are ordered properly
        form.instance.reorder_course_activities()


@admin.register(Activity)
class ActivityAdmin(ModelAdmin):
    form = ActivityAdminUpdateForm
    list_display = ("id", "name", "author", "published", "updated")
    list_display_links = ("id", "name")
    readonly_fields = ("slug",)

    class ActivityCollaboratorsInline(TabularInline):
        model = ActivityCollaborator
        readonly_fields = ("created", "updated",)
        extra = 0

    class ObjectiveOnActivityInline(TabularInline):
        model = ActivityObjective
        readonly_fields = ('taxonomy_level', 'objective', 'objective_reusable', 'created')
        extra = 0

    inlines = [
        ActivityCollaboratorsInline,
        ObjectiveOnActivityInline
    ]


@admin.register(Resource)
class ResourceAdmin(ModelAdmin):
    form = ResourceAdminUpdateForm
    list_display = ("id", "name", "type", "author", "published", "updated")
    list_display_links = ("id", "name")
    list_filter = ("type", "published")
    readonly_fields = ("slug",)

    class ResourceCollaboratorsInline(TabularInline):
        model = ResourceCollaborator
        readonly_fields = ("created", "updated",)
        extra = 0

    class ObjectiveOnResourceInline(TabularInline):
        model = ResourceObjective
        readonly_fields = ('taxonomy_level', 'objective', 'objective_reusable', 'created')
        extra = 0

    inlines = [
        ResourceCollaboratorsInline,
        ObjectiveOnResourceInline,
    ]


@admin.register(Objective)
class ObjectiveAdmin(ModelAdmin):
    form = ObjectiveAdminCreateForm
    list_display = ('id', 'ability', 'language')
    list_display_links = ('id', 'ability')


@admin.register(CourseObjective)
class CourseObjectiveAdmin(ModelAdmin):
    form = CourseObjectiveAdminCreateForm
    list_display = ('id', 'objective', 'course', 'taxonomy_level', 'objective_reusable')
    list_display_links = ('id', 'objective', 'course')


@admin.register(ActivityObjective)
class ActivityObjectiveAdmin(ModelAdmin):
    form = ActivityObjectiveAdminCreateForm
    list_display = ('id', 'objective', 'activity', 'taxonomy_level', 'objective_reusable')
    list_display_links = ('id', 'objective', 'activity')


@admin.register(ResourceObjective)
class ResourceObjectiveAdmin(ModelAdmin):
    form = ResourceObjectiveAdminCreateForm
    list_display = ('id', 'objective', 'resource', 'taxonomy_level', 'objective_reusable')
    list_display_links = ('id', 'objective', 'resource')
