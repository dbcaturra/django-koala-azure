/**
 * Copyright (C) 2019-2020 Guillaume Bernard <guillaume.bernard@koala-lms.org>
 * Copyright (C) 2020 Thomas Blot <thomasblot16@gmail.com>
 *
 * This file is part of Koala LMS (Learning Management system)

 * Koala LMS is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
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
 *
 */

let select_id_access = document.getElementById("id_access")
if (select_id_access) {
    select_id_access.addEventListener("click", function update_state_and_access_listener() {
        let selected = document.getElementById("id_access").value;
        let state = document.getElementById("id_state");
        switch (selected) {
            // FIXME: This code works but is not maintainable
            // display the correct state, filter by access selected
            case'PUBLIC':
                state.children[0].style.display = "none";
                state.children[1].style.display = "block";
                state.children[2].style.display = "block";
                break;
            case'STUDENTS_ONLY':
                state.children[0].style.display = "none";
                state.children[1].style.display = "block";
                state.children[2].style.display = "block";
                break;
            case'COLLABORATORS_ONLY':
                state.children[0].style.display = "block";
                state.children[1].style.display = "block";
                state.children[2].style.display = "block";
                break;
            case'PRIVATE':
                state.children[0].style.display = "block";
                state.children[1].style.display = "none";
                state.children[2].style.display = "block";
                break;
        }
    });
}

let add_form_exists = (document.getElementsByName("object_add_form").length === 1);
if (add_form_exists) {
    function display_tab(tab_index) {
        // This function will display the specified tab of the form, and buttons
        let all_tabs = document.getElementsByClassName("object_form_tab");
        let current_tab_is_last_tab = tab_index === (all_tabs.length);
        let current_tab_is_penultimate_tab = tab_index === (all_tabs.length - 1);
        if (current_tab_is_last_tab) {
            document.getElementsByClassName("progress_tab")[tab_index - 1].classList.add("active");
            document.getElementById("next_tab_btn").style.display = "none";
            if (document.getElementById("add_course_submit_button")) {
                document.getElementById("add_course_submit_button").style.display = "block";
            }
            if (document.getElementById("add_resource_submit_button")) {
                document.getElementById("add_resource_submit_button").style.display = "block";
            }
            if (document.getElementById("add_activity_submit_button")) {
                document.getElementById("add_activity_submit_button").style.display = "block";
            }
        } else {
            all_tabs[tab_index].style.display = "block";
            let current_tab_item = document.getElementsByClassName("progress_tab");
            if (tab_index > 0) {
                current_tab_item[tab_index - 1].classList.add("active");
            }
            if (tab_index < all_tabs.length) {
                current_tab_item[tab_index].classList.remove("active");
            }
            let current_tab_is_first_tab = (current_tab_number === 0);
            if (current_tab_is_first_tab) {
                document.getElementById("previous_tab_btn").style.display = "none";
            } else {
                document.getElementById("previous_tab_btn").style.display = "inline";
                document.getElementById("next_tab_btn").style.display = "inline";
                if (document.getElementById("add_course_submit_button")) {
                    document.getElementById("add_course_submit_button").style.display = "none";
                }
                if (document.getElementById("add_resource_submit_button")) {
                    document.getElementById("add_resource_submit_button").style.display = "none";
                }
                if (document.getElementById("add_activity_submit_button")) {
                    document.getElementById("add_activity_submit_button").style.display = "none";
                }
            }
            if (current_tab_is_penultimate_tab) {
                document.getElementById("next_tab_btn").style.display = "inline";
            }

        }
    }

    /**
     * Switch between form tabs.
     *
     * @param n the index (positive or negative) that indicates how to iterate over tabs. 1 means switching to the next
     * one, while -1 means switching to the previous one.
     */
    function switch_tab(n) {
        // This function manage the switch of pages
        let all_tabs = document.getElementsByClassName("object_form_tab");
        if ((current_tab_number + n) === (all_tabs.length)) {
            // if user click on resume, send the user to the last page
            for (let current_tab_index = 0; current_tab_index < all_tabs.length - 1; current_tab_index++) {
                all_tabs[current_tab_index].style.display = "block";
            }
            current_tab_number += n;
            display_tab(current_tab_number);
        } else {
            if ((current_tab_number) === (all_tabs.length)) {
                // if the user is on the last page, and return to the penultimate tab
                for (let current_tab_index = 0; current_tab_index < all_tabs.length - 1; current_tab_index++) {
                    all_tabs[current_tab_index].style.display = "none";
                    all_tabs[current_tab_number + n].style.display = "block";
                }
                current_tab_number += n;
                display_tab(current_tab_number);
            } else {
                // Common case increment or decrement the page and display
                all_tabs[current_tab_number].style.display = "none";
                all_tabs[current_tab_number + n].style.display = "block";
                current_tab_number += n;
                display_tab(current_tab_number);
            }
        }
    }

    document.getElementById("next_tab_btn").style.display = "block";
    document.getElementById("previous_tab_btn").style.display = "block";

    resource_add_form = document.getElementById("resource_add_form");
    if (resource_add_form) {
        document.getElementById("add_resource_submit_button").style.display = "none";
        document.getElementById("resource_form_progress_bar").style.display = "block";
    }

    activity_add_form = document.getElementById("activity_add_form");
    if (activity_add_form) {
        document.getElementById("add_activity_submit_button").style.display = "none";
        document.getElementById("activity_form_progress_bar").style.display = "block";
    }

    course_add_form = document.getElementById("course_add_form");
    if (course_add_form) {
        document.getElementById("add_course_submit_button").style.display = "none";
        document.getElementById("course_form_progress_bar").style.display = "block";
    }

    document.getElementsByClassName("form-group")[0].style.backgroundColor = "#f7f7f7";
    let all_tabs = document.getElementsByClassName("object_form_tab");
    Array.prototype.forEach.call(all_tabs, function (tab) {
        tab.style.display = "none";
    });

    let current_tab_number = 0;
    display_tab(0);
}

let desc;
document.addEventListener("keydown", KeyCheck);

// The KeyCheck function allows the system to count the number of characters at the press of the "Backspace" and "Delete" character deletion keys.
function KeyCheck(event) {
     let KeyID = event.keyCode;
     switch(KeyID)
     {
        case 8:
          desc = document.getElementById("id_description");
          if(desc.value.length > 0){
              let s = interpolate(ngettext('%s character', '%s characters',desc.value.length - 1),[desc.value.length - 1]);
            document.getElementById("nb_char").innerHTML = s
          }
        break;
        case 46:
          desc = document.getElementById("id_description");
          if(desc.value.length > 0){
              let s = interpolate(ngettext('%s character', '%s characters',desc.value.length - 1),[desc.value.length - 1]);
            document.getElementById("nb_char").innerHTML = s
          }
        break;
        default:
        break;
     }
}
function count_up() {
    desc = document.getElementById("id_description");
    let s = interpolate(ngettext('%s character', '%s characters',desc.value.length + 1),[desc.value.length + 1]);
    document.getElementById("nb_char").innerHTML = s;
}

if (document.getElementById("id_existing_ability"))
{
    let input_create_ability = document.getElementById("id_ability");
    let input_existing_ability = document.getElementById("id_existing_ability");


    input_existing_ability.addEventListener("change", function update_add_objective_form() {
        input_create_ability.disabled = input_existing_ability[input_existing_ability.selectedIndex].value !== "";
});
}


