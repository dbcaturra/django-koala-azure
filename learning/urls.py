#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
#
# Copyright (C) 2020 Dervin Enard <dervin@hotmail.fr>
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

from django.urls import path, include
from django.views.i18n import JavaScriptCatalog

import learning.views.activity as activity_views
import learning.views.course as course_views
import learning.views.resource as resource_views
import learning.views.objective as objective_view

from learning.views.views import WelcomePageView

app_name = "learning"  # Application namespace

###############
# Course ULRs #
###############

course_details_urlpatterns = [
    # The course itself
    path("", course_views.CourseDetailView.as_view(), name="course/detail"),

    # Access courses similar to the current one
    path("similar/", course_views.CourseDetailSimilarView.as_view(), name="course/detail/similar"),

    # Registration on a course, for a student
    path("register", course_views.CourseRegisterView.as_view(), name="course/detail/register"),
    path("unregister", course_views.CourseUnregisterView.as_view(), name="course/detail/unregister"),

    # Activities: view (as student and as teacher), add, unlink and delete from a course
    path("activities", course_views.CourseDetailActivitiesView.as_view(), name="course/detail/activities"),
    path(
        "activity/<slug:activity_slug>/",
        course_views.CourseDetailActivitiesView.as_view(),
        name="course/detail/activity"
    ),
    path(
        "activity/<slug:activity_slug>/resource/<slug:resource_slug>",
        course_views.CourseDetailActivityResourceView.as_view(),
        name="course/detail/activities/resource"
    ),
    path("activity/up", course_views.activity_on_course_up_view, name="course/detail/activity/up"),
    path("activity/add", course_views.ActivityCreateOnCourseView.as_view(), name="course/detail/activity/add"),
    path("activity/attach", course_views.ActivityAttachOnCourseView.as_view(), name="course/detail/activity/attach"),
    path("activity/unlink", course_views.activity_on_course_unlink_view, name="course/detail/activity/unlink"),
    path("activity/delete", course_views.activity_on_course_delete_view, name="course/detail/activity/delete"),

    # Collaborators: view, add and delete from a course
    path("collaborators", course_views.CourseDetailCollaboratorsListView.as_view(), name="course/detail/collaborators"),
    path("collaborator/add", course_views.CourseDetailCollaboratorsAddView.as_view(),
         name="course/detail/collaborator/add"),
    path("collaborator/update", course_views.CourseDetailCollaboratorsChangeView.as_view(),
         name="course/detail/collaborator/change"),
    path("collaborator/delete", course_views.CourseDetailCollaboratorsDeleteView.as_view(),
         name="course/detail/collaborator/delete"),

    # Students: view, add and delete from a course
    path("students/", course_views.CourseDetailStudentsView.as_view(), name="course/detail/students"),
    path("students/add", course_views.CourseDetailStudentsAddView.as_view(), name="course/detail/students/add"),
    path("students/update/<int:registration_pk>", course_views.CourseDetailStudentChangeView.as_view(),
         name="course/detail/students/change"),
    path("students/delete", course_views.CourseDetailStudentsDeleteView.as_view(),
         name="course/detail/students/delete"),
    path('students/', course_views.CourseDetailStudentsView.as_view(), name="course/detail/students"),
    path('students/add', course_views.CourseDetailStudentsAddView.as_view(), name="course/detail/students/add"),
    path('students/update', course_views.CourseDetailStudentChangeView.as_view(),
         name="course/detail/students/change"),
    path('students/delete', course_views.CourseDetailStudentsDeleteView.as_view(),
         name="course/detail/students/delete"),

    # Objective : add, delete, view objective

    path('objectives', course_views.CourseDetailObjectiveListView.as_view(),
         name="course/detail/objectives"),

    path('objective/add', course_views.CourseDetailObjectiveAddView.as_view(),
         name="course/detail/objective/add"),

    path('objective/remove', course_views.CourseDetailObjectiveRemoveView.as_view(),
         name="course/detail/objective/remove"),

    path('objective/change', course_views.CourseDetailObjectiveUpdateView.as_view(),
         name="course/detail/objective/change"),

    path('objective/validation/change', course_views.CourseObjectiveUpdateValidationView.as_view(),
         name="course/detail/objective/validation/change"),

    # Progression

    path('progression/student', course_views.StudentCourseProgressionMixin.as_view(),
         name="course/detail/progression/student"),


    path('progression/teacher', course_views.TeacherCourseProgressionMixin.as_view(),
         name="course/detail/progression/teacher"),

    path('progression/teacher/<int:username_id>', course_views.TeacherCourseProgressionMixin.as_view(),
         name="course/detail/progression/teacher/"),

]

course_urlpatterns = [
    path("study", course_views.CourseAsStudentListView.as_view(), name="course/my"),
    path("study/favourite/<slug:course_slug>", course_views.CourseFavouriteAsStudentListView.as_view(),
         name="course/my/favourite"),
    path("teach/", course_views.CourseAsTeacherListView.as_view(), name="course/teaching"),
    path("teach/favourite/<slug:course_slug>", course_views.CourseFavouriteAsTeacherListView.as_view(),
         name="course/teaching/favourite"),
    path("search/", course_views.CourseSearchView.as_view(), name="course/search"),

    # Course view, add, update and delete views
    path("add/", course_views.CourseCreateView.as_view(), name="course/add"),
    path("update/<slug:slug>/", course_views.CourseUpdateView.as_view(), name="course/update"),
    path("delete/<slug:slug>/", course_views.CourseDeleteView.as_view(), name="course/delete"),
    path("detail/<slug:slug>/", include(course_details_urlpatterns)),

]

#################
# Activity ULRs #
#################

activity_details_urlpatterns = [
    # The activity itself
    path("", activity_views.ActivityDetailView.as_view(), name="activity/detail"),

    # Add a new resource on this activity
    path("resource/add", activity_views.ActivityCreateResourceView.as_view(), name="activity/detail/resource/add"),
    path("resource/attach", activity_views.ResourceAttachOnActivityView.as_view(),
         name="activity/detail/resource/attach"),
    path("resource/unlink", activity_views.ResourceUnlinkOnActivityView.as_view(),
         name="activity/detail/resource/unlink"),
    path("resource/detail/<slug:resource_slug>", activity_views.ResourceOnActivityDetailView.as_view(),
         name="activity/resource/detail"),

    # By which courses the activity is used
    path("usage/", activity_views.ActivityDetailUsageView.as_view(), name="activity/detail/usage"),

    # Activities similar to the current one
    path("similar/", activity_views.ActivityDetailSimilarView.as_view(), name="activity/detail/similar"),

    # Collaborators: view, add and delete from a course
    path("collaborators", activity_views.ActivityDetailCollaboratorsListView.as_view(),
         name="activity/detail/collaborators"),
    path("collaborator/add", activity_views.ActivityDetailCollaboratorsAddView.as_view(),
         name="activity/detail/collaborator/add"),
    path("collaborator/update", activity_views.ActivityDetailCollaboratorsChangeView.as_view(),
         name="activity/detail/collaborator/change"),
    path("collaborator/delete", activity_views.ActivityDetailCollaboratorsDeleteView.as_view(),
         name="activity/detail/collaborator/delete"),

    # Objective : add, delete, view objective

    path('objectives', activity_views.ActivityDetailObjectiveListView.as_view(),
         name="activity/detail/objectives"),

    path('objective/add', activity_views.ActivityDetailObjectiveAddView.as_view(),
         name="activity/detail/objective/add"),

    path('objective/change', activity_views.ActivityDetailObjectiveUpdateView.as_view(),
         name="activity/detail/objective/change"),

    path('objective/remove', activity_views.ActivityDetailObjectiveRemoveView.as_view(),
         name="activity/detail/objective/remove"),

    path('objective/validation/change', activity_views.ActivityObjectiveUpdateValidationView.as_view(),
         name="activity/detail/objective/validation/change"),


]

activity_urlpatterns = [
    path("", activity_views.ActivityListView.as_view(), name="activity/my"),
    path("favourite/<slug:activity_slug>", activity_views.ActivityFavouriteListView.as_view(),
         name="activity/my/favourite"),

    # Activity view, add, update and delete views
    path("add/", activity_views.ActivityCreateView.as_view(), name="activity/add"),
    path("delete/<slug:slug>/", activity_views.ActivityDeleteView.as_view(), name="activity/delete"),
    path("update/<slug:slug>/", activity_views.ActivityUpdateView.as_view(), name="activity/update"),
    path("detail/<slug:slug>/", include(activity_details_urlpatterns)),
]

#################
# Resource ULRs #
#################

resource_details_urlpatterns = [
    # The resource itself
    path("", resource_views.ResourceDetailView.as_view(), name="resource/detail"),

    # By which activities the activity is used
    path("usage/", resource_views.ResourceDetailUsageView.as_view(), name="resource/detail/usage"),

    # Resources similar to the current one
    path("similar/", resource_views.ResourceDetailSimilarView.as_view(), name="resource/detail/similar"),

    # Collaborators: view, add and delete from a course
    path("collaborators", resource_views.ResourceDetailCollaboratorsListView.as_view(),
         name="resource/detail/collaborators"),
    path("collaborator/add", resource_views.ResourceDetailCollaboratorsAddView.as_view(),
         name="resource/detail/collaborator/add"),
    path("collaborator/update", resource_views.ResourceDetailCollaboratorsChangeView.as_view(),
         name="resource/detail/collaborator/change"),
    path("collaborator/delete", resource_views.ResourceDetailCollaboratorsDeleteView.as_view(),
         name="resource/detail/collaborator/delete"),

    # Objective : add, delete, view objective

    path('objectives', resource_views.ResourceDetailObjectiveListView.as_view(),
         name="resource/detail/objectives"),

    path('objective/add', resource_views.ResourceDetailObjectiveAddView.as_view(),
         name="resource/detail/objective/add"),

    path('objective/change', resource_views.ResourceDetailObjectiveUpdateView.as_view(),
         name="resource/detail/objective/change"),

    path('objective/remove', resource_views.ResourceDetailObjectiveRemoveView.as_view(),
         name="resource/detail/objective/remove"),

    path('objective/validation/change', resource_views.ResourceObjectiveUpdateValidationView.as_view(),
         name="resource/detail/objective/validation/change"),
]

resource_urlpatterns = [
    path("", resource_views.ResourceListView.as_view(), name="resource/my"),
    path("favourite/<slug:resource_slug>", resource_views.ResourceFavouriteListView.as_view(),
         name="resource/my/favourite"),
    # Resource view, add, update and delete views
    path("add/", resource_views.ResourceCreateView.as_view(), name="resource/add"),

    path("delete/<slug:slug>/", resource_views.ResourceDeleteView.as_view(), name="resource/delete"),
    path("update/<slug:slug>/", resource_views.ResourceUpdateView.as_view(), name="resource/update"),
    path("detail/<slug:slug>/", include(resource_details_urlpatterns)),
]

##################
# Objective URLs #
##################

objective_urlpatterns = [
    path('', objective_view.ObjectiveListView.as_view(), name='objective'),
    path('create', objective_view.ObjectiveCreateView.as_view(), name='objective/create'),
    path('delete', objective_view.ObjectiveDeleteView.as_view(), name='objective/delete'),
    path('detail/<slug:slug>', objective_view.ObjectiveDetailView.as_view(), name='objective/detail'),

]

####################
# Application URLs #
####################
urlpatterns = [
    path("", WelcomePageView.as_view(), name="index"),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path("course/", include(course_urlpatterns)),
    path("activity/", include(activity_urlpatterns)),
    path("resource/", include(resource_urlpatterns)),
    path('objective/', include(objective_urlpatterns))
]
