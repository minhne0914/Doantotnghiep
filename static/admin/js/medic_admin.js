(function () {
    function normalizedPath(url) {
        try {
            return new URL(url, window.location.origin).pathname.replace(/\/+$/, "");
        } catch (error) {
            return "";
        }
    }

    function directChild(element, selector) {
        for (var i = 0; i < element.children.length; i += 1) {
            if (element.children[i].matches(selector)) {
                return element.children[i];
            }
        }
        return null;
    }

    function setExpanded(item, expanded) {
        var link = directChild(item, ".nav-link");
        var submenu = directChild(item, ".nav-treeview");

        if (!submenu) {
            return;
        }

        item.classList.toggle("menu-open", expanded);
        submenu.style.display = expanded ? "block" : "none";

        if (link) {
            link.setAttribute("aria-expanded", expanded ? "true" : "false");
            link.classList.toggle("active", expanded || submenu.querySelector(".nav-link.active"));
        }
    }

    function setupSidebarTree() {
        var currentPath = window.location.pathname.replace(/\/+$/, "");
        var treeItems = document.querySelectorAll(".main-sidebar .nav-item.has-treeview");

        treeItems.forEach(function (item) {
            var link = directChild(item, ".nav-link");
            var submenu = directChild(item, ".nav-treeview");

            if (!link || !submenu) {
                return;
            }

            link.setAttribute("role", "button");
            link.setAttribute("aria-expanded", "false");

            var hasCurrentChild = Array.prototype.some.call(
                submenu.querySelectorAll("a.nav-link[href]"),
                function (childLink) {
                    var isCurrent = normalizedPath(childLink.href) === currentPath;
                    childLink.classList.toggle("active", isCurrent);
                    return isCurrent;
                }
            );

            setExpanded(item, hasCurrentChild);

            link.addEventListener("click", function (event) {
                event.preventDefault();

                var shouldOpen = !item.classList.contains("menu-open");
                var parentList = item.parentElement;

                if (parentList) {
                    Array.prototype.forEach.call(
                        parentList.querySelectorAll(":scope > .nav-item.has-treeview.menu-open"),
                        function (sibling) {
                            if (sibling !== item) {
                                setExpanded(sibling, false);
                            }
                        }
                    );
                }

                setExpanded(item, shouldOpen);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupSidebarTree);
    } else {
        setupSidebarTree();
    }
}());
