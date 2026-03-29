document.addEventListener('DOMContentLoaded', function() {
    const sprintDropdownBtn = document.getElementById('sprintDropdownBtn');
    const sprintDropdownMenu = document.getElementById('sprintDropdownMenu');

    if (!sprintDropdownBtn || !sprintDropdownMenu) {
        return;
    }

    const items = sprintDropdownMenu.querySelectorAll('.dropdown-item');

    function showDropdownAnimated() {
        sprintDropdownMenu.style.display = 'block';

        items.forEach(function(item) {
            item.style.transition = 'opacity 0.35s cubic-bezier(.4,2,.6,1), transform 0.35s cubic-bezier(.4,2,.6,1)';
            item.style.opacity = '0';
            item.style.transform = 'translateY(-10px)';
        });

        setTimeout(function() {
            items.forEach(function(item, i) {
                setTimeout(function() {
                    item.style.opacity = '1';
                    item.style.transform = 'translateY(0)';
                }, i * 90);
            });
        }, 10);
    }

    function hideDropdownAnimated() {
        items.forEach(function(item, i) {
            setTimeout(function() {
                item.style.opacity = '0';
                item.style.transform = 'translateY(-10px)';
            }, (items.length - i - 1) * 50);
        });

        setTimeout(function() {
            sprintDropdownMenu.style.display = 'none';
        }, items.length * 50 + 200);
    }

    let open = false;

    sprintDropdownBtn.addEventListener('click', function(e) {
        e.stopPropagation();

        if (!open) {
            showDropdownAnimated();
        } else {
            hideDropdownAnimated();
        }

        open = !open;
    });

    document.addEventListener('click', function(e) {
        if (!sprintDropdownMenu.contains(e.target) && e.target !== sprintDropdownBtn && open) {
            hideDropdownAnimated();
            open = false;
        }
    });

    items.forEach(function(item) {
        item.style.opacity = '0';
        item.style.transform = 'translateY(-10px)';
    });
});
