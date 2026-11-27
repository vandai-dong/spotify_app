window.onload = function() {
    const today = new Date().toISOString().split('T')[0]; // Get today's date in the format YYYY-MM-DD
    document.getElementById('birthdate').setAttribute('max', today); // Set the max attribute
};

let currentStep = 1;
const totalSteps = 3;
const stepDesriptions = ["Create a password", "Tell us about yourself", "Confirm Your Details"];

// Function to show a specific step
function showStep() {
    // Clear all alerts
    clearAlerts();

    // Update the step number
    document.getElementById("step-number").innerHTML = `Step ${currentStep} of 3`;

    // Update the step description
    document.getElementById("step-description").innerHTML = stepDesriptions[currentStep - 1];

    // Update the progress bar
    const progressPercentage = (currentStep / totalSteps) * 100;
    document.getElementById('progress-bar').style.width = `${progressPercentage}%`;
    document.getElementById('progress-bar').setAttribute('aria-valuenow', progressPercentage.toFixed(2));       

    for (let i = 1; i <= totalSteps; i++) {
        document.getElementById(`step-${i}`).style.display = (i === currentStep) ? 'block' : 'none';
    }
}

// Function to handle navigation to the previous page
function handleBackLink() {
    if (currentStep === 1) {
        // Navigate to the signup page if on the first step
        window.location.href = signUpUrl;
    } else {
        // Otherwise, go to the previous step
        previousStep();
    }
}

// Function to move to the next step
function nextStep() {
    if (currentStep < totalSteps) {
        // If on Step 1, validate the password before proceeding
        if (currentStep === 1) {
            if (!validatePassword()) {
                // Ensure the password meets all criteria before proceeding
                const alertElm = document.getElementById("error-message");
                alertElm.className = 'alert alert-danger'; // Set classes
                alertElm.role = 'alert'; // Set role attribute
                alertElm.innerHTML = "Please enter the valid password.";

                // Clear password input fields
                document.getElementById("password").value = "";

                // Unchecked all radio buttons
                document.getElementById('password').value = "";
                document.getElementById('letter-criteria').checked = false;
                document.getElementById('number-special-criteria').checked = false;
                document.getElementById('length-criteria').checked = false;

                return;
            }
        } else if (currentStep === 2) {
            if (!validatePersonalInfo()) {
                // Ensure the password meets all criteria before proceeding
                const alertElm = document.getElementById("error-message");
                alertElm.className = 'alert alert-danger'; // Set classes
                alertElm.role = 'alert'; // Set role attribute
                alertElm.innerHTML = "Please fill out all required fields.";
                return;
            }
        }
        currentStep++;
        showStep(currentStep);
    }
}

// Function to move to the previous step
function previousStep() {
    if (currentStep > 1) {
        currentStep--;
        if (currentStep == 1) {
            // Delete the previous password stored and unchecked all radio buttons
            document.getElementById('password').value = "";
            document.getElementById('letter-criteria').checked = false;
            document.getElementById('number-special-criteria').checked = false;
            document.getElementById('length-criteria').checked = false;
        }
        // showStep(currentStep);
        showStep();
    }
}

// Function to validate the password
function validatePassword() {
    const password = document.getElementById('password').value;

    // Define criteria
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumberOrSpecial = /[0-9!@#$%^&*(),.?":{}|<>]/.test(password);
    const hasMinLength = password.length >= 10;

    // Update checkboxes based on criteria
    document.getElementById('letter-criteria').checked = hasLetter;
    document.getElementById('number-special-criteria').checked = hasNumberOrSpecial;
    document.getElementById('length-criteria').checked = hasMinLength;

    // Return true only if all criteria are met
    return hasLetter && hasNumberOrSpecial && hasMinLength;
}

function validatePersonalInfo() {
    let isValid = true;

    // Get the inputs in the current step
    const inputs = document.querySelectorAll(`#step-2 input[required]`);

    // Check each required input
    // inputs.forEach(input => {
    //     if (!input.value) {
    //         isValid = false;
    //         input.style.borderColor = 'red'; // Highlight the input field
    //     } else {
    //         input.style.borderColor = ''; // Reset border color if valid
    //     }
    // });
    inputs.forEach(input => {
        if (!input.value) {
            isValid = false;
        }
    });

    // Check if there are any radio buttons for gender and if one is selected
    const genderRadios = document.querySelectorAll(`#step-2 input[name="gender"]`);
    const genderSelected = Array.from(genderRadios).some(radio => radio.checked);
    
    // if (genderRadios.length > 0 && !genderSelected) {
    //     isValid = false;
    //     genderRadios[0].parentElement.style.borderColor = 'red'; // Highlight the gender section
    // } else {
    //     genderRadios[0].parentElement.style.borderColor = ''; // Reset if valid
    // }

    if (genderRadios.length > 0 && !genderSelected) {
        isValid = false;
    }

    return isValid;
}

function clearAlerts() {
    const errorMessageDiv = document.getElementById("error-message");
    errorMessageDiv.innerHTML = ""; // Clear the inner HTML of the error message div
    errorMessageDiv.className = ""; // Optionally, remove any existing alert classes
    errorMessageDiv.removeAttribute('role'); // Remove role attribute
}


// Function to validate all steps before submission
function validateAllSteps() {
    // Optionally, add more validations for other steps here
    return true; // Allow form submission
}

// Initialize the first step on page load
document.addEventListener('DOMContentLoaded', function() {
    showStep();
});