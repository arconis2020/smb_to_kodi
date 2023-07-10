// Get the object from storage or make a new one.
let opened = sessionStorage.getItem("opened") || new Array()
// If the object comes from storage, it's a string, so parse it.
if (typeof(opened) == "string") {
    opened = JSON.parse(opened);
}
// Use a map here for O1 access to individual IDs.
opened = new Map(opened);

function expandAndContractHidables(buttonElement) {
    // Return true if the content was expanded, false otherwise. Facilitates parent expansion.
    // This is the collapsible button
    buttonElement.classList.toggle("active");
    let expanded = false;
    // This is the div under the collapsible button.
    let content = buttonElement.nextElementSibling;
    if (content.style.maxHeight){
        // Unset any max height as part of the click toggle.
        content.style.maxHeight = null;
        // Remove this button from the auto-open list.
        opened.delete(buttonElement.id);
    } else {
        // Set the max height as part of the click toggle.
        content.style.maxHeight = content.scrollHeight + "px";
        expanded = true;
        // Add the button to the auto-open list.
        opened.set(buttonElement.id, "true");
    }
    // Store the auto-open list in session storage immediately to allow refreshes.
    sessionStorage.setItem("opened", JSON.stringify(Array.from(opened.entries())));
    // Return the expanded boolean to allow continuation to the expandParents function.
    return expanded
}

function expandParents(currentElement) {
    // Start at the element that was expanded, and work upward to expand.
    let totalHeight = currentElement.scrollHeight;
    while (currentElement.parentNode) {
        // The current element was already expanded, so move up and check.
        currentElement = currentElement.parentNode;
        // Only expand elements that are divs with a class of "hidable".
        if (currentElement.tagName == "DIV" && currentElement.classList.contains("hidable")) {
            // Total height is a running total of all child divs up to the parent.
            totalHeight = totalHeight + currentElement.scrollHeight;
            currentElement.style.maxHeight = totalHeight + "px";
        }
    }
}

async function setUpFolderButtons() {
    await buildFolderList();  // found in ./folder_sort.js
    const coll = document.getElementsByClassName("collapsible");
    for (let i = 0; i < coll.length; i++) {
        // Add click listeners.
        coll[i].addEventListener("click", function() {
            let content = this.nextElementSibling;
            let expanded = expandAndContractHidables(this);
            if (expanded) {
                expandParents(content);
            }
        });
        // Click for the user on things that should be open by default.
        if (coll[i].classList.contains("default-open") || opened.has(coll[i].id)) {
            coll[i].click();
        }
    }
}
