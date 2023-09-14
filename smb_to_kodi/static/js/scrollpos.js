document.addEventListener("DOMContentLoaded", function(event) { 
    var scrollpos = sessionStorage.getItem('scrollpos');
    if (scrollpos) {
        // This timeout is required because rendering takes several ms after .onload.
        setTimeout(() => {
            window.scrollTo(0, scrollpos);
        }, 500);
    }
});

window.onbeforeunload = function(e) {
    sessionStorage.setItem('scrollpos', window.scrollY);
};
