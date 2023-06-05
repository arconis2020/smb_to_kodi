function expand_and_contract_hidables(button_element) {
    // Return true if the content was expanded, false otherwise. Facilitates parent expansion.
    button_element.classList.toggle("active");
    var expanded = false;
    var content = button_element.nextElementSibling;
    if (content.style.maxHeight){
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = content.scrollHeight + "px";
      expanded = true;
    }
    return expanded
}

function expand_parents(current_element) {
    // Start at the element that was expanded, and work upward to expand.
    var total_height = current_element.scrollHeight;
    while (current_element.parentNode) {
        // The current element was already expanded, so move up and check.
        current_element = current_element.parentNode;
        if (current_element.tagName == "DIV" && current_element.classList.contains("hidable")) {
          total_height = total_height + current_element.scrollHeight;
          current_element.style.maxHeight = total_height + "px";
        }
    }
}

var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
    // Add click listeners first.
    coll[i].addEventListener("click", function() {
        var content = this.nextElementSibling;
        var expanded = expand_and_contract_hidables(this);
        if (expanded) {
            expand_parents(content);
        }
    });
    // Click for the user on things that should be open by default.
    if (coll[i].classList.contains("default-open")) {
        coll[i].click();
    }
}
