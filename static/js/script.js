function deleteAddress(del_id) {
    $.ajax({
        method: 'POST',
        url: '/deleteaddress',
        contentType: 'application/json',  // Ensure JSON is sent
        data: JSON.stringify({
            del_id: del_id
        }),
        success: function (response) {
            console.log(response.message);
            if (response.status === 'success') {
                alert(response.message);
                window.location.href = '/showaddress'
            } else {
                alert(response.message);
                window.location.href = '/showaddress'
            }
        },
        error: function () {
            alert("An error occurred while trying to delete the address.");
        }
    });
}