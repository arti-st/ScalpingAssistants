async function updateTable() {

    try {

        const response = await fetch("/api/sizes");

        if (!response.ok) {
            throw new Error("HTTP " + response.status);
        }

        const sizes = await response.json();

        // sizes.sort(compareSizes);

        sizes.sort((a, b) => {

            const statusA = getBreakthroughStatus(a);
            const statusB = getBreakthroughStatus(b);

            console.log(
                a.coin,
                "vs",
                b.coin,
                "|",
                statusA.text,
                "vs",
                statusB.text
            );

            const statusOrder = {
                "open": 0,
                "open/crossed": 1,
                "crossed": 2,
                "n/a": 3
            };

            return statusOrder[statusA.text] - statusOrder[statusB.text];
        });


        const tableBody =
            document.getElementById("sizes-table");

        tableBody.innerHTML = "";

        for (const size of sizes) {

            const row =
                document.createElement("tr");

            /*
             * REPEAT COUNTER HIGHLIGHT
             */

            if (size.continuous_counter >= REPEAT_COUNTER) {
                row.classList.add("repeat-highlight");
            }

            const directionSymbol =
                size.direction === "up"
                    ? "↗"
                    : "↘";

            const breakthrough =
                getBreakthroughStatus(size);

            row.innerHTML = `

                <td>
                    ${formatDate(size.signal_date)}
                </td>

                <td>
                    ${escapeHtml(size.coin)}
                </td>

                <td>
                    ${formatNumber(size.size_price)}
                </td>

                <td>
                    ${formatNumber(size.extremum_price)}
                </td>

                <td>
                    ${formatNumber(size.current_price)}
                </td>

                <td>
                    ${directionSymbol}
                    ${formatNumber(size.distance)}%
                </td>

                <td>
                    x${formatNumber(size.size_vs_max_neighbor, 1)}
                </td>

                <td>
                    x${formatNumber(size.size_vs_avg_volume, 1)}
                </td>

                <td>
                    ${formatTime(size.first_seen)}
                </td>

                <td>
                    ${formatTime(size.last_seen)}
                </td>

                <td>
                    ${size.continuous_counter}
                    (${size.total_counter})
                </td>

                <td class="${breakthrough.className}">
                    ${breakthrough.text}
                </td>

            `;

            tableBody.appendChild(row);
        }

    } catch (error) {

        console.error(
            "Failed to update table:",
            error
        );

    }
}


function compareSizes(a, b) {

    // 1. Date - newest date first

    const dateComparison =
        b.signal_date.localeCompare(a.signal_date);

    if (dateComparison !== 0) {
        return dateComparison;
    }


    // 2. Breakthrough

    const breakthroughOrder = {
        "open": 0,
        "open/crossed": 1,
        "crossed": 2,
        "n/a": 3
    };

    const breakthroughA =
        getBreakthroughStatus(a).text;

    const breakthroughB =
        getBreakthroughStatus(b).text;

    const breakthroughComparison =
        breakthroughOrder[breakthroughA]
        -
        breakthroughOrder[breakthroughB];

    if (breakthroughComparison !== 0) {
        return breakthroughComparison;
    }


    // 3. Distance bucket

    const distanceBucketA =
        Math.floor(Math.abs(a.distance));

    const distanceBucketB =
        Math.floor(Math.abs(b.distance));

    if (distanceBucketA !== distanceBucketB) {
        return distanceBucketA - distanceBucketB;
    }


    // 4. Continuous counter - highest first

    const counterComparison =
        b.continuous_counter
        -
        a.continuous_counter;

    if (counterComparison !== 0) {
        return counterComparison;
    }


    // 5. First signal - oldest first

    return b.last_seen.localeCompare(a.last_seen);
}


function getBreakthroughStatus(size) {

    if (!size.active) {

        return {
            text: "n/a",
            className: "removed"
        };
    }

    const crossed =
        size.direction === "up"
            ? size.current_price > size.size_price
            : size.current_price < size.size_price;

    if (crossed) {

        return {
            text: "crossed",
            className: "crossed"
        };
    }

    if (size.ever_crossed) {

        return {
            text: "open/crossed",
            className: "open-crossed"
        };
    }

    return {
        text: "open",
        className: "open"
    };
}


function formatDate(value) {

    const parts = value.split("-");

    return (
        parts[2] +
        "." +
        parts[1] +
        "." +
        parts[0].slice(2)
    );
}


function formatTime(value) {

    return value.substring(11, 19);
}


function formatNumber(value, decimals = 8) {

    return Number(value).toLocaleString(
        undefined,
        {
            maximumFractionDigits: decimals
        }
    );
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/*
 * THEME
 */

const themeToggle =
    document.getElementById("theme-toggle");


themeToggle.addEventListener("click", () => {

    document.body.classList.toggle("dark");

    const isDark =
        document.body.classList.contains("dark");

    themeToggle.textContent =
        isDark
            ? "☀️ Day"
            : "🌙 Night";

    localStorage.setItem(
        "theme",
        isDark
            ? "dark"
            : "light"
    );
});


/*
 * Restore previous theme
 */

if (localStorage.getItem("theme") === "dark") {

    document.body.classList.add("dark");

    themeToggle.textContent = "☀️ Day";
}


/*
 * INITIAL LOAD + REFRESH
 */

updateTable();

setInterval(updateTable, 1000);
