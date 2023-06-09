// Get the object from storage or make a new one.
var opened = sessionStorage.getItem("opened") || new Array()
// If the object comes from storage, it's a string, so parse it.
if (typeof(opened) == "string") {
    var opened = JSON.parse(opened);
}
// Use a map here for O1 access to individual IDs.
var opened = new Map(opened);

function expand_and_contract_hidables(button_element) {
    // Return true if the content was expanded, false otherwise. Facilitates parent expansion.
    // This is the collapsible button
    button_element.classList.toggle("active");
    var expanded = false;
    // This is the div under the collapsible button.
    var content = button_element.nextElementSibling;
    if (content.style.maxHeight){
      // Unset any max height as part of the click toggle.
      content.style.maxHeight = null;
      // Remove this button from the auto-open list.
      opened.delete(button_element.id);
    } else {
      // Set the max height as part of the click toggle.
      content.style.maxHeight = content.scrollHeight + "px";
      expanded = true;
      // Add the button to the auto-open list.
      opened.set(button_element.id, "true");
    }
    // Store the auto-open list in session storage immediately to allow refreshes.
    sessionStorage.setItem("opened", JSON.stringify(Array.from(opened.entries())));
    // Return the expanded boolean to allow continuation to the expand_parents function.
    return expanded
}

function expand_parents(current_element) {
    // Start at the element that was expanded, and work upward to expand.
    var total_height = current_element.scrollHeight;
    while (current_element.parentNode) {
        // The current element was already expanded, so move up and check.
        current_element = current_element.parentNode;
        // Only expand elements that are divs with a class of "hidable".
        if (current_element.tagName == "DIV" && current_element.classList.contains("hidable")) {
          // Total height is a running total of all child divs up to the parent.
          total_height = total_height + current_element.scrollHeight;
          current_element.style.maxHeight = total_height + "px";
        }
    }
}

var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
    // Add repeatable IDs to all buttons using the buttons' inner text.
    if (!coll[i].getAttribute("id")) {
        coll[i].setAttribute("id", coll[i].innerText);
    }
    // Add click listeners.
    coll[i].addEventListener("click", function() {
        var content = this.nextElementSibling;
        var expanded = expand_and_contract_hidables(this);
        if (expanded) {
            expand_parents(content);
        }
    });
    // Click for the user on things that should be open by default.
    if (coll[i].classList.contains("default-open") || opened.has(coll[i].id)) {
        coll[i].click();
    }
}
