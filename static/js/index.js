
console.log("Welcome");
const button = document.getElementById("test");

function buttonHandler(){
    document.getElementById("test").innerHTML = "CHANGED";
}

button.addEventListener("click", buttonHandler);
