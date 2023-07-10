const URL = window.location.href + "/json_content"
async function fetchJsonContent() {
    const response = await fetch(URL);
    if (!response.ok) {
        // Many pages won't have a /json_content, so return quickly and move on.
        return null;
    }
    const sortables = await response.json();
    return sortables;
}

const fragment = document.createDocumentFragment();
/* 
It's important to note that the function below isn't "sorting" everything in the traditional sense.
It IS sorting each div, button, and para into their appropriate parent-child relationships, but you'll notice
that it is NOT sorting each level of the nested parent-child structure alphabetically. Yet the end-result
on the user's browser screen is actually sorted alphanumerically. The reason for this additional and very 
desirable level of sorting is actually the INPUT to this function, which is a JSON object whose keys have 
ALREADY been sorted.  The Django backend providing this data should always have "sort_keys=True".
*/
async function buildFolderList() {
    const sortables = await fetchJsonContent();
    if (!sortables) {
        return null;
    }
    // Install the divs first.
    const divCache = {};
    for (const [key, divObj] of Object.entries(sortables.divs)) {
        // Create a new div of "hidable" class.
        newDiv = document.createElement("div");
        newDiv.setAttribute("id", divObj.myid);
        newDiv.setAttribute("class", "hidable");
        // The flexbase container is not in the fragment, so add its children at the root.
        if (divObj.parent == "flexbase") {
            // This will be the only thing you add directly to the fragment.
            fragment.append(newDiv);
        } else {
            // Anything else should be added directly to the parent element.
            divCache[divObj.parent].appendChild(newDiv);
        }
        divCache[divObj.myid] = newDiv;
    }
    // Install the buttons.
    for (const [key, buttonObj] of Object.entries(sortables.buttons)) {
        // Create a new button of "collapsible" class that will be the first entry in a div.
        newButton = document.createElement("button");
        newButton.setAttribute("id", buttonObj.myid);
        newButton.setAttribute("class", "collapsible");
        newButton.textContent = buttonObj.displayname;
        // These buttons are guaranteed to have parents in the divCache, as that's the whole point of the struture.
        divCache[buttonObj.parent].insertBefore(newButton, divCache[buttonObj.sibling]);
    }
    // Install the paras. DO NOT convert this to text-based elements.
    /* Caching the para objects like this instead of using fragment.getElement... increases the speed of this
       for loop by 3 orders of magnitude for a ~17,000 song music collection. Using direct fragment functions took
       just over 10 seconds, and using this paraCache feature took 186ms.
    */
    const paraCache = {};
    for (const [smbPath, paraObj] of Object.entries(sortables.paras)) {
        lastWatched = (paraObj.last_watched !== null) ? paraObj.last_watched : '';
        // Create a new <p> element to hold all the file-related content.
        newPara = document.createElement("p");
        newPara.setAttribute("style", "margin: 0px;");
        // Create a new button of "jsplay" class with the special play button character.
        playButton = document.createElement("button");
        playButton.setAttribute("class", "jsplay");
        playButton.setAttribute("value", smbPath);
        playButton.setAttribute("style", "margin: 12px;");
        playButton.textContent = "\u25B6";
        // Add the basename of the file in a span after the button to ensure easy element placement.
        txtSpan = document.createElement("span");
        txtSpan.textContent = paraObj.displayname;
        // Add the last-watched date, if any, to a color-coded span that comes after the basename.
        lwSpan = document.createElement("span");
        lwSpan.setAttribute("style", "color: #3092F5;");
        lwSpan.textContent = `  ${lastWatched}`;
        // Wrap the important elements in the <p>.
        newPara.append(...[playButton, txtSpan, lwSpan]);
        if (!paraCache[paraObj.parent]) {
            // Add the new <p> to the paraCache if it wasn't there, using a list to allow many <p>s.
            paraCache[paraObj.parent] = [newPara];
        } else {
            // Add to the list of <p>s already present.
            paraCache[paraObj.parent].push(newPara);
        }
    }
    // Add the <p>s to their respective parent <div>s en masse.
    for (const [parentId, paras] of Object.entries(paraCache)) {
        // Do NOT use innerHTML here, as it leads to incomplete documents.
        divCache[parentId].append(...paras);
    }
    // Now put the fragment in the DOM by replacing the designated div.
    document.getElementById("replaceme").replaceWith(fragment);
}
