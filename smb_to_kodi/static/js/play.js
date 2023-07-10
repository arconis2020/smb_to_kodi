const csrftoken = document.cookie
    .split(";")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];

async function setUpPlayButtons() {
    await setUpFolderButtons();  // Found in ./collapsibles.js
    const button_collection = document.getElementsByClassName("jsplay");
    for (const button of button_collection) {
        button.addEventListener("click", function() {
            const XHR = new XMLHttpRequest();
            const FD = new FormData();
            FD.append("smb_path", button.value);
            // Define what happens on successful data submission
            XHR.addEventListener("load", (event) => {
                location.reload();
            });
            // Define what happens in case of an error
            XHR.addEventListener("error", (event) => {
                alert("Oops! Something went wrong.");
            });
            XHR.open("POST", "play");
            XHR.setRequestHeader("X-CSRFToken", csrftoken);
            XHR.send(FD);
        });
    }
}
setUpPlayButtons();
