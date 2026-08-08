// Noesis frontend scripts

console.log("Noesis loaded");


// Keep the search box in sync with the current query

const search = document.querySelector(".searchbox input");

if (search && search.value) {

    search.setSelectionRange(
        search.value.length,
        search.value.length
    );

}


// Upload feedback

const uploadForm = document.querySelector("form[enctype]");

if (uploadForm) {

    uploadForm.addEventListener("submit", function () {

        const btn = uploadForm.querySelector("button[type=submit]");

        if (btn) {
            btn.textContent = "Publishing\u2026";
            btn.disabled = true;
        }

    });

}
