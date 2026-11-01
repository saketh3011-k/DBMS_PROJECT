// Main JavaScript for Student Attendance Management System

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle for Mobile View
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener('click', function () {
            sidebar.classList.toggle('d-none');
        });
    }

    // 2. Auto Dismiss Flash Alerts after 5 seconds
    setTimeout(function () {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // 3. Mark All Present / Absent Buttons in Faculty Attendance Form
    const markAllPresentBtn = document.getElementById('markAllPresentBtn');
    const markAllAbsentBtn = document.getElementById('markAllAbsentBtn');

    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', function () {
            document.querySelectorAll('input[type="radio"][value="Present"]').forEach(function (radio) {
                radio.checked = true;
            });
        });
    }

    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', function () {
            document.querySelectorAll('input[type="radio"][value="Absent"]').forEach(function (radio) {
                radio.checked = true;
            });
        });
    }

    // 4. Live Table Search Filter
    const liveSearchInput = document.getElementById('liveTableSearch');
    if (liveSearchInput) {
        liveSearchInput.addEventListener('keyup', function () {
            const filter = liveSearchInput.value.toLowerCase();
            const rows = document.querySelectorAll('#filterableTable tbody tr');
            rows.forEach(function (row) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.indexOf(filter) > -1 ? '' : 'none';
            });
        });
    }
});

// Demo credential quick-filler function for login page
function fillLogin(identifier, password, role) {
    const idInput = document.getElementById('identifier');
    const pwdInput = document.getElementById('password');
    const roleSelect = document.getElementById('role');
    
    if (idInput) idInput.value = identifier;
    if (pwdInput) pwdInput.value = password;
    if (roleSelect && role) roleSelect.value = role;
}
