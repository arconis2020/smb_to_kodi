function set_light_dark() {
    const dm = localStorage.getItem("darkMode");  // Treated as a string
    if (dm === "true") {
        var element = document.body;
        if (! element.classList.contains("dark-mode")) {
            element.classList.toggle("dark-mode");
        }
    }
}
function toggle_light_dark() {
    var element = document.body;
    element.classList.toggle("dark-mode");
    localStorage.setItem("darkMode", element.classList.contains("dark-mode"));
}
