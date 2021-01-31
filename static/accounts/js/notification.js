/**
 * Copyright (C) 2019-2020 Guillaume Bernard <guillaume.bernard@koala-lms.org>
 * Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
 *
 *  This file is part of Koala LMS (Learning Management system)
 *
 * Koala LMS is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or*
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * We make an extensive use of the Django framework, https://www.djangoproject.com/
 */

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Disable propagation for the notification dropdown: ensures it is not closed on each click
let notification_dropdown = document.getElementById("notifications_dropdown");
if (notification_dropdown) {
    notification_dropdown.addEventListener("click", function (e) {
        e.stopPropagation()
    });
}

/**
 *
 * @param responseText
 */
function update_notification_counter(responseText) {
    let unread_nb = JSON.parse(responseText)['unread'];
    let counter = document.getElementById("notification_counter");
    if (counter) {
        if (unread_nb > 0) {
            counter.innerText = unread_nb;
        } else {
            counter.remove();
        }
    }
}

/**
 * Sends an Ajax request to the server in order to set a notification as read.
 * Works only if the notification_id belongs the currently logged-in user.
 *
 * @param notification_id the notification unique identifier.
 */
function notification_mark_as_read(notification_id){

  let counter = document.getElementById("notification_counter");
  let nb_notification = + counter.innerText;
  setTimeout(x => {
    for (let i = 0; i < nb_notification; i++) {
      document.getElementById('notification_' + notification_id + '_message').classList.add("text-muted");
      let csrftoken = getCookie('csrftoken');
      let xhr = new XMLHttpRequest();
      xhr.open('POST', "/accounts/ajax/notification/read/" + notification_id, true);
      if (csrftoken) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        xhr.onreadystatechange = function () {
          if (xhr.readyState === 4 && xhr.status === 200) {
                counter.remove();
          }
        };
        xhr.send()
      } else {
        console.log('CSRF token is not set');
      }
      notification_id = notification_id + 1;
    }
  }
  ,3000);
}

/**
 * Sends an Ajax request to the server to delete a notification.
 * Works only if the notification_id belongs the currently logged-in user.
 *
 * @param notification_id the notification identifier
 */
function notification_delete(notification_id) {
    let csrftoken = getCookie('csrftoken');
    let xhr = new XMLHttpRequest();
    xhr.open('POST', "/accounts/ajax/notification/delete/" + notification_id, true);
    if (csrftoken) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                update_notification_counter(xhr.responseText);

                // Remove the notification and its corresponding divider
                document.getElementById("notification_" + notification_id).remove();
                let divider = document.getElementById("notification_divider_" + notification_id);
                if (divider) {
                    divider.remove();
                }

                // Close the notification dropdown if there is not any notification
                let dropdown = document.getElementById("notifications_dropdown");
                if (dropdown.children.length === 0) {
                    dropdown.remove()
                }
            }
        };
        xhr.send()
    } else {
        console.log('CSRF token is not set');
    }
}

