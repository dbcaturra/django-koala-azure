$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});

$("#id_username").on("input", function () {
    let username = $(this).val();
    $.ajax({
        url: '/accounts/ajax/search/',
        data: {
            'user': username
        },
        dataType: 'json',
        success: function (data) {
            let user_list = $("#user_list");
            user_list.empty();
            for (let i = 0; i < data.length; i++) {
                // noinspection JSUnresolvedVariable
                let label = data[i].first_name + ' ' + data[i].last_name + ' (@' + data[i].username +  ')';
                user_list.append("<option value='" + data[i].username + "' label='" + label + "'></option>");
            }
        }
    });
});

function copyLink() {
    let dummy = document.createElement('input'),
        text = document.getElementById('copy-link-button').value;

    document.body.appendChild(dummy);
    dummy.value = text;
    dummy.select();
    document.execCommand('copy');
    document.getElementById("alert-copy-link").style.display = "block";
    setTimeout(x=> {document.getElementById("alert-copy-link").style.display = "none";},5000);
    document.body.removeChild(dummy);
}

function dropdown() {
    let dropdown = document.getElementsByClassName("btn-dropdown");
    let icn = document.getElementsByClassName("icn-dropdown");
    let i;
    for (i = 0; i < dropdown.length; i++) {
        icn[i].classList.toggle("fa-caret-down");
        icn[i].classList.toggle("fa-caret-up");
        dropdown[i].classList.toggle("bg-light");
        dropdown[i].classList.toggle("active");
        let dropdownContent = document.getElementById("dropdown-container");
        if (dropdownContent.style.display === "block") {
            dropdownContent.style.display = "none";
        } else {
            dropdownContent.style.display = "block";
        }
    }
}
