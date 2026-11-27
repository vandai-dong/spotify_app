function validatePassword() {
    // Get the values from the password and confirm password fields
    var password = document.getElementById("password").value;
    var confirm_password = document.getElementById("confirm-password").value;

    // Access the error message element
    var errorMessage = document.getElementById("error-message");

    // Check if errorMessage element exists before manipulating it
    if (errorMessage) {
        // Clear any previous error message
        errorMessage.classList.remove("alert", "alert-danger");
        errorMessage.removeAttribute("role");
        errorMessage.textContent = "";
    }

    // Check if the passwords match
    if (password !== confirm_password) {
        if (errorMessage) {
            // Set error message text
            errorMessage.textContent = "Passwords do not match!";
            
            // Add Bootstrap classes dynamically
            errorMessage.classList.add("alert", "alert-danger");
            
            // Set the role attribute for accessibility
            errorMessage.setAttribute("role", "alert");
        }
        return false; // Prevent form submission
    }

    return true; // Allow form submission
}