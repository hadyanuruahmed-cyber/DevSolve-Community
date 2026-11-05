document.addEventListener("DOMContentLoaded", function () {

    // SHARE IDEAS FORM
    const feedbackForm = document.querySelector(
        "#feedback form"
    );

    if (feedbackForm) {
        feedbackForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const submitButton = feedbackForm.querySelector(
                'button[type="submit"]'
            );

            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Submitting...";

            try {
                const response = await fetch(feedbackForm.action, {
                    method: "POST",
                    body: new FormData(feedbackForm),
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const result = await response.json();

                let notice = document.querySelector(
                    "#feedback .flash-message"
                );

                if (!notice) {
                    notice = document.createElement("p");
                    notice.className = "flash-message";
                    feedbackForm.parentNode.insertBefore(
                        notice,
                        feedbackForm
                    );
                }

                notice.textContent = result.message;
                notice.style.display = "block";

                if (response.ok && result.success) {
                    feedbackForm.reset();

                    notice.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest"
                    });
                }

            } catch (error) {
                alert(
                    "We couldn't submit your feedback. Please try again."
                );

            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }


    // REPORT A SCHOOL PROBLEM FORM
    const problemForm = document.querySelector(
        "#report form"
    );

    if (problemForm) {
        problemForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const submitButton = problemForm.querySelector(
                'button[type="submit"]'
            );

            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Submitting...";

            try {
                const response = await fetch(problemForm.action, {
                    method: "POST",
                    body: new FormData(problemForm),
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const result = await response.json();

                let notice = document.querySelector(
                    "#report .flash-message"
                );

                if (!notice) {
                    notice = document.createElement("p");
                    notice.className = "flash-message";

                    problemForm.parentNode.insertBefore(
                        notice,
                        problemForm
                    );
                }

                notice.textContent = result.message;
                notice.style.display = "block";

                if (response.ok && result.success) {
                    problemForm.reset();

                    notice.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest"
                    });
                }

            } catch (error) {
                alert(
                    "We couldn't submit your report. Please try again."
                );

            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
       // MEMBERSHIP APPLICATION FORM
    const applicationForm = document.querySelector(
        "#join form.application-form"
    );

    if (applicationForm) {

        const fullName = applicationForm.querySelector("#full_name");
        const phone = applicationForm.querySelector("#phone");
        const grade = applicationForm.querySelector("#grade_section");
        const email = applicationForm.querySelector("#email");
        const roleReason = applicationForm.querySelector("#role_reason");
        const motivation = applicationForm.querySelector("#motivation");
        const roleSelection = applicationForm.querySelector(".role-selection");

        const touched = new Set();

        // Create a feedback message underneath a field
        function createFeedback(element, id) {
            let message = document.getElementById(id);

            if (!message) {
                message = document.createElement("small");
                message.id = id;
                message.className = "live-validation";
                message.style.display = "block";
                message.style.marginTop = "6px";

                if (element === roleSelection) {
                    element.insertAdjacentElement("afterend", message);
                } else {
                    element.insertAdjacentElement("afterend", message);
                }
            }

            return message;
        }

        const feedback = {
            fullName: createFeedback(fullName, "name-feedback"),
            phone: createFeedback(phone, "phone-feedback"),
            grade: createFeedback(grade, "grade-feedback"),
            email: createFeedback(email, "email-feedback"),
            role: createFeedback(roleSelection, "role-feedback"),
            roleReason: createFeedback(roleReason, "role-reason-feedback"),
            motivation: createFeedback(motivation, "motivation-feedback")
        };

        // Character counters
        function createCounter(element, id, maximum) {
            const counter = document.createElement("small");
            counter.id = id;
            counter.style.display = "block";
            counter.style.marginTop = "5px";
            counter.style.color = "#64748b";

            element.insertAdjacentElement("afterend", counter);

            function update() {
                counter.textContent =
                    `${element.value.length} / ${maximum} characters`;
            }

            element.addEventListener("input", update);
            update();

            return counter;
        }

        createCounter(roleReason, "role-reason-counter", 300);
        createCounter(motivation, "motivation-counter", 1000);

        // Show validation messages
        function showFeedback(element, message, valid) {
            element.textContent = message;
            element.style.color = valid ? "#15803d" : "#dc2626";
            element.style.fontWeight = "500";
        }

        // Validate full name
        function validateName() {
            const value = fullName.value.trim();
            const parts = value.split(/\s+/);

            const valid =
                value.length <= 100 &&
                parts.length >= 2 &&
                parts.every(part =>
                    /^[A-Za-z]+(?:[-'][A-Za-z]+)*$/.test(part)
                );

            showFeedback(
                feedback.fullName,
                valid
                    ? "✓ Full name looks good."
                    : "Please enter your first name and last name using letters only.",
                valid
            );

            return valid;
        }

        // Validate Ethiopian phone number
        function validatePhone() {
            const value = phone.value.replace(/[\s()-]/g, "");

            const valid = /^(?:\+251|0)(?:9|7)\d{8}$/.test(value);

            showFeedback(
                feedback.phone,
                valid
                    ? "✓ Valid Ethiopian mobile number."
                    : "Enter a valid number, e.g. 0912345678 or +251912345678.",
                valid
            );

            return valid;
        }

        // Validate grade
        function validateGrade() {
            const valid = [
                "Grade 9",
                "Grade 10",
                "Grade 11",
                "Grade 12"
            ].includes(grade.value);

            showFeedback(
                feedback.grade,
                valid ? "✓ Grade selected." : "Please select your grade.",
                valid
            );

            return valid;
        }

        // Validate email
        function validateEmail() {
            const value = email.value.trim();

            const valid =
                value.length <= 254 &&
                /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);

            showFeedback(
                feedback.email,
                valid
                    ? "✓ Email address looks valid."
                    : "Please enter a valid email address.",
                valid
            );

            return valid;
        }

        // Validate selected role
        function validateRole() {
            const selected = applicationForm.querySelector(
                'input[name="role"]:checked'
            );

            const valid = Boolean(selected);

            showFeedback(
                feedback.role,
                valid
                    ? "✓ Role selected."
                    : "Please select one role.",
                valid
            );

            return valid;
        }

        // Validate role explanation
        function validateRoleReason() {
            const length = roleReason.value.trim().length;

            const valid = length >= 20 && length <= 300;

            showFeedback(
                feedback.roleReason,
                valid
                    ? "✓ Role explanation looks good."
                    : `Please write between 20 and 300 characters. Current: ${length}.`,
                valid
            );

            return valid;
        }

        // Validate motivation
        function validateMotivation() {
            const length = motivation.value.trim().length;

            const valid = length >= 50 && length <= 1000;

            showFeedback(
                feedback.motivation,
                valid
                    ? "✓ Motivation looks good."
                    : `Please write between 50 and 1000 characters. Current: ${length}.`,
                valid
            );

            return valid;
        }

        // Connect live validation to fields
        const validators = [
            [fullName, "fullName", validateName],
            [phone, "phone", validatePhone],
            [grade, "grade", validateGrade],
            [email, "email", validateEmail],
            [roleReason, "roleReason", validateRoleReason],
            [motivation, "motivation", validateMotivation]
        ];

        validators.forEach(([element, key, validator]) => {
            element.addEventListener("input", function () {
                touched.add(key);
                validator();
            });

            element.addEventListener("change", function () {
                touched.add(key);
                validator();
            });
        });

        applicationForm.querySelectorAll(
            'input[name="role"]'
        ).forEach(radio => {
            radio.addEventListener("change", function () {
                touched.add("role");
                validateRole();
            });
        });

        // CUSTOM CONFIRMATION WINDOW
        function showApplicationConfirmation() {
            return new Promise((resolve) => {
                const modal = document.createElement("div");

                modal.className = "application-modal";
                modal.innerHTML = `
                    <div class="application-modal-card">
                        <div class="modal-icon">✓</div>
                        <h2>Ready to submit?</h2>
                        <p>
                            Please make sure all your information
                            is accurate and complete.
                        </p>

                        <div class="modal-reminder">
                            <strong>What happens next?</strong>
                            <p>
                                Your application will be reviewed.
                                You will receive the result within
                                one week. Please check your inbox
                                and spam folder.
                            </p>
                        </div>

                        <div class="modal-actions">
                            <button type="button" class="modal-cancel">
                                Go Back
                            </button>
                            <button type="button" class="modal-confirm">
                                Confirm Submission
                            </button>
                        </div>
                    </div>
                `;

                document.body.appendChild(modal);

                function closeModal(answer) {
                    modal.remove();
                    resolve(answer);
                }

                modal.querySelector(".modal-cancel")
                    .addEventListener("click", () => closeModal(false));

                modal.querySelector(".modal-confirm")
                    .addEventListener("click", () => closeModal(true));

                modal.addEventListener("click", (event) => {
                    if (event.target === modal) {
                        closeModal(false);
                    }
                });
            });
        }

        // SUBMIT APPLICATION
        applicationForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            // Validate every field before submission
            touched.add("fullName");
            touched.add("phone");
            touched.add("grade");
            touched.add("email");
            touched.add("role");
            touched.add("roleReason");
            touched.add("motivation");

            const checks = [
                validateName(),
                validatePhone(),
                validateGrade(),
                validateEmail(),
                validateRole(),
                validateRoleReason(),
                validateMotivation()
            ];

            if (checks.includes(false)) {
                const firstInvalid = validators.find(
                    ([element, key, validator]) => !validator()
                );

                if (firstInvalid) {
                    firstInvalid[0].scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });

                    firstInvalid[0].focus();
                }

                return;
            }

            if (!applicationForm.reportValidity()) {
                return;
            }

            const confirmed = await showApplicationConfirmation();

            if (!confirmed) {
                return;
            }

            const submitButton = applicationForm.querySelector(
                'button[type="submit"]'
            );

            const originalText = submitButton.textContent;

            let notice = document.querySelector(
                "#join .application-notice"
            );

            if (!notice) {
                notice = document.createElement("div");
                notice.className = "application-notice";
                notice.setAttribute("aria-live", "polite");

                applicationForm.parentNode.insertBefore(
                    notice,
                    applicationForm
                );
            }

            submitButton.disabled = true;
            submitButton.textContent = "Submitting...";

            try {
                const response = await fetch(applicationForm.action, {
                    method: "POST",
                    body: new FormData(applicationForm),
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const result = await response.json();

                notice.textContent = result.message;

                if (response.ok && result.success) {
                    notice.className =
                        "application-notice application-success";

                    notice.setAttribute("role", "status");

                    applicationForm.reset();
                    applicationForm.style.display = "none";
                    const announcement = document.querySelector(
    "#join .application-announcement"
);

if (announcement) {
    announcement.style.display = "none";
}

                } else {
                    notice.className =
                        "application-notice application-error";

                    notice.setAttribute("role", "alert");
                }

                notice.style.display = "block";

                notice.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });

            } catch (error) {
                notice.textContent =
                    "We couldn't submit your application. Please try again.";

                notice.className =
                    "application-notice application-error";

                notice.setAttribute("role", "alert");
                notice.style.display = "block";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
});