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


class LearningError(Exception):
    """
    Basic learning package exception
    """


#######################
# Resource exceptions #
#######################


class ResourceNotReusableError(LearningError):
    """
    The resource cannot be reused by anyone
    """


class ResourceAlreadyOnActivityError(LearningError):
    """
    The resource is already linked with an activity
    """


class ResourceNotReusableOnlyAuthorError(LearningError):
    """
    The resource is not reusable, except for its author
    """


class ResourceIsNotLinkedWithThisActivityError(LearningError):
    """
    The resource is not linked with the activity
    """


#######################
# Activity exceptions #
#######################

class ActivityNotReusableOnlyAuthorError(LearningError):
    """
    The activity cannot be reused by anyone
    """


class ActivityAlreadyOnCourseError(LearningError):
    """
    The activity is already linked with a course
    """


class ActivityNotReusableError(LearningError):
    """
    The activity is not reusable
    """


class ActivityIsNotLinkedWithThisCourseError(LearningError):
    """
    The activity is not linked with the course
    """


#####################
# Course exceptions #
#####################


class CannotRegisterOnCourseError(LearningError):
    """
    It is not possible to register on a course
    """


class RegistrationDisabledError(LearningError):
    """
    Registration is disabled on a course
    """


class CannotAddCollaboratorOnCourseError(LearningError):
    """
    It is not possible to add a collaborator on a course
    """


class ChangeActivityOnCourseError(LearningError):
    """
    It is not possible to change the activity on a course
    """


class UserIsAlreadyCollaborator(LearningError):
    """
    The user is already a collaborator on the course
    """


class UserIsAlreadyAuthor(LearningError):
    """
    The user is already author on the course
    """


class UserNotCollaboratorError(LearningError):
    """
    The user is not a collaborator on the course
    """


class UserIsNotStudent(LearningError):
    """
    The user is not a student on the course
    """


class UserIsAlreadyStudent(LearningError):
    """
    The user is already a student on the course
    """


####################
# Model exceptions #
####################
class ObjectiveAlreadyInModel(LearningError):
    """
    The competence is already in the model
    """


class ObjectiveNotInModel(LearningError):
    """
    The competence is not in the model
    """


class ObjectiveAlreadyExists(LearningError):
    """
    The course_objective exists
    """


class ObjectiveAbilityCannotBeEmpty(LearningError):
    """
    The ability cannot be empty
    """


class ObjectiveIsAlreadyValidated(LearningError):
    """
    The course_objective is already validated
    """


class ObjectiveIsNotValidated(LearningError):
    """
    The course_objective is not validated
    """
