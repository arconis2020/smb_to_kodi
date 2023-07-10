function setLightDark() {
    const dm = localStorage.getItem("darkMode");  // Treated as a string
    if (dm === "true") {
        let element = document.body;
        if (! element.classList.contains("dark-mode")) {
            element.classList.toggle("dark-mode");
        }
    }
}
function toggleLightDark() {
    let element = document.body;
    element.classList.toggle("dark-mode");
    localStorage.setItem("darkMode", element.classList.contains("dark-mode"));
}
