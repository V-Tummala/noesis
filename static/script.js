// Noesis Frontend Scripts


console.log(
    "Noesis loaded"
);



// Confirm before leaving upload page

const uploadForm = document.querySelector(
    "form[enctype]"
);


if(uploadForm){


    uploadForm.addEventListener(
        "submit",
        function(){

            console.log(
                "Uploading resource..."
            );

        }
    );

}