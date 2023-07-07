var children = document.querySelectorAll('[data-parent]');
children.forEach((child) => {
    this_pid = child.getAttribute("data-parent");
    current_pid = child.parentElement.id;
    if (this_pid != current_pid) {
        this_sibling = child.getAttribute("data-sibling");
        if (!this_sibling) {
            document.getElementById(this_pid).appendChild(child);
        } else {
            document.getElementById(this_pid).insertBefore(child, document.getElementById(this_sibling));
        }
    }
});
children.forEach((child) => {
    child.style.display = "block";
});
