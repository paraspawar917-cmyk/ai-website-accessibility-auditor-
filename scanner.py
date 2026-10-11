import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (AccessAI Accessibility Auditor)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_target_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = f"https://{url}"

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL format: {raw_url}")
    return url


def truncate_html(element, max_len=180) -> str:
    if not element:
        return ""
    # Render opening tag or snippet
    html = str(element).strip()
    # Normalize whitespaces
    html = re.sub(r"\s+", " ", html)
    if len(html) > max_len:
        return html[:max_len] + "..."
    return html


def build_selector(element) -> str:
    if not element:
        return ""
    tag = element.name or "element"
    elem_id = element.get("id")
    if elem_id:
        return f"{tag}#{elem_id}"
    classes = element.get("class")
    if classes and isinstance(classes, list):
        class_str = "." + ".".join(classes[:2])
        return f"{tag}{class_str}"
    name = element.get("name")
    if name:
        return f"{tag}[name='{name}']"
    src = element.get("src")
    if src:
        src_short = src.split("/")[-1].split("?")[0]
        return f"{tag}[src*='{src_short[:25]}']"
    href = element.get("href")
    if href:
        href_short = href.split("?")[0][:25]
        return f"{tag}[href='{href_short}']"
    return f"<{tag}>"


def audit_website(url: str):
    target_url = normalize_target_url(url)

    try:
        response = requests.get(
            target_url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
            verify=True,
        )
    except requests.exceptions.SSLError:
        # Fallback to verify=False if SSL handshake fails on self-signed/dev certs
        response = requests.get(
            target_url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
            verify=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to access {target_url}: {str(exc)}")

    if response.status_code >= 400:
        raise RuntimeError(f"Website responded with HTTP status {response.status_code}")

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    final_url = response.url

    issues = []
    passed_checks = 0

    # 1. Check: <html> lang attribute (WCAG 3.1.1)
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang") or not html_tag.get("lang").strip():
        issues.append({
            "rule_code": "html-has-lang",
            "issue_title": "<html> element missing a valid lang attribute",
            "description": "The root <html> element does not specify a language attribute, preventing screen readers from choosing the correct accent and speech rules.",
            "severity": "serious",
            "wcag": "WCAG 3.1.1",
            "element": "<html>",
            "element_html": truncate_html(html_tag) if html_tag else "<html>",
            "recommendation": "Add a lang attribute to the <html> tag, for example: <html lang=\"en\">.",
        })
    else:
        passed_checks += 1

    # 2. Check: Document <title> (WCAG 2.4.2)
    title_tag = soup.find("title")
    if not title_tag or not title_tag.string or not title_tag.string.strip():
        issues.append({
            "rule_code": "document-title",
            "issue_title": "Document title missing or empty",
            "description": "The web page does not contain a descriptive <title> in the <head>, making it difficult for screen reader users and browser tab navigation.",
            "severity": "serious",
            "wcag": "WCAG 2.4.2",
            "element": "<title>",
            "element_html": truncate_html(title_tag) if title_tag else "<head>",
            "recommendation": "Add a unique and descriptive <title> inside the <head> element that summarizes the page content.",
        })
    else:
        passed_checks += 1

    # 3. Check: Images missing alt or generic alt (WCAG 1.1.1)
    images = soup.find_all("img")
    images_passed = 0
    generic_alts = {"image", "photo", "picture", "logo", "icon", "graphic", "placeholder", "untitled"}

    for img in images:
        alt = img.get("alt")
        selector = build_selector(img)
        html_snippet = truncate_html(img)

        # Check if img is inside a link
        is_linked = bool(img.find_parent("a"))

        if alt is None:
            if is_linked:
                parent_a = img.find_parent("a")
                parent_text = parent_a.get_text(strip=True) if parent_a else ""
                if not parent_text:
                    issues.append({
                        "rule_code": "image-link-alt-missing",
                        "issue_title": "Linked image missing alternative text",
                        "description": "An image inside an anchor link lacks an alt attribute and the link has no text, leaving assistive technology unable to announce the link destination.",
                        "severity": "critical",
                        "wcag": "WCAG 1.1.1",
                        "element": selector,
                        "element_html": html_snippet,
                        "recommendation": "Provide an alt attribute describing the link destination, or add descriptive link text / aria-label on the parent <a>.",
                    })
                    continue
            issues.append({
                "rule_code": "image-alt-missing",
                "issue_title": "Images missing alternative text",
                "description": "Some images do not have alternative text for screen-reader users.",
                "severity": "serious",
                "wcag": "WCAG 1.1.1",
                "element": selector,
                "element_html": html_snippet,
                "recommendation": "Add a descriptive alt attribute to meaningful images. Use alt=\"\" for purely decorative images.",
            })
        else:
            alt_clean = alt.strip().lower()
            if alt_clean in generic_alts or re.search(r"\.(png|jpg|jpeg|gif|webp|svg)$", alt_clean):
                issues.append({
                    "rule_code": "image-alt-generic",
                    "issue_title": "Image alternative text is generic or a file name",
                    "description": f"The image alt attribute '{alt}' uses a generic placeholder or filename instead of explaining the image content.",
                    "severity": "minor",
                    "wcag": "WCAG 1.1.1",
                    "element": selector,
                    "element_html": html_snippet,
                    "recommendation": "Replace generic alt text with a meaningful description of what the image shows.",
                })
            else:
                images_passed += 1

    if images and images_passed > 0:
        passed_checks += min(images_passed, 5)
    elif not images:
        passed_checks += 1

    # 4. Check: Form inputs missing labels (WCAG 4.1.2 & 1.3.1)
    inputs = soup.find_all(["input", "textarea", "select"])
    inputs_passed = 0

    for field in inputs:
        tag_name = field.name
        input_type = (field.get("type") or "text").lower()
        if tag_name == "input" and input_type in ("hidden", "submit", "reset", "button", "image"):
            continue

        field_id = field.get("id")
        has_label = False

        if field_id:
            label = soup.find("label", attrs={"for": field_id})
            if label and label.get_text(strip=True):
                has_label = True

        if not has_label:
            parent_label = field.find_parent("label")
            if parent_label and parent_label.get_text(strip=True):
                has_label = True

        if not has_label:
            if field.get("aria-label") or field.get("aria-labelledby") or field.get("title"):
                has_label = True

        if not has_label:
            selector = build_selector(field)
            issues.append({
                "rule_code": "form-field-label",
                "issue_title": f"Form field missing accessible label ({tag_name})",
                "description": f"A form control ({selector}) does not have an associated <label> or aria-label.",
                "severity": "serious",
                "wcag": "WCAG 4.1.2",
                "element": selector,
                "element_html": truncate_html(field),
                "recommendation": "Associate a descriptive <label for=\"...\"> with the input, or provide an appropriate aria-label attribute.",
            })
        else:
            inputs_passed += 1

    if inputs and inputs_passed > 0:
        passed_checks += min(inputs_passed, 4)
    elif not inputs:
        passed_checks += 1

    # 5. Check: Buttons missing accessible names (WCAG 4.1.2)
    buttons = soup.find_all("button")
    buttons_passed = 0

    for btn in buttons:
        btn_text = btn.get_text(strip=True)
        has_name = bool(btn_text or btn.get("aria-label") or btn.get("aria-labelledby") or btn.get("title"))
        if not has_name:
            # check child img with alt
            img = btn.find("img")
            if img and img.get("alt"):
                has_name = True

        if not has_name:
            selector = build_selector(btn)
            issues.append({
                "rule_code": "button-name",
                "issue_title": "Button missing accessible name",
                "description": "A button contains no text content or aria-label, leaving screen reader users unaware of its action.",
                "severity": "critical",
                "wcag": "WCAG 4.1.2",
                "element": selector,
                "element_html": truncate_html(btn),
                "recommendation": "Add visible text inside the <button> or add an aria-label attribute describing what clicking it does.",
            })
        else:
            buttons_passed += 1

    if buttons and buttons_passed > 0:
        passed_checks += min(buttons_passed, 3)
    elif not buttons:
        passed_checks += 1

    # 6. Check: Links missing discernible text or vague link text (WCAG 2.4.4)
    links = soup.find_all("a", href=True)
    links_passed = 0
    vague_texts = {"click here", "read more", "learn more", "more", "here", "link", "view", "details"}

    for a in links:
        link_text = a.get_text(strip=True)
        selector = build_selector(a)
        html_snippet = truncate_html(a)

        has_name = bool(link_text or a.get("aria-label") or a.get("aria-labelledby") or a.get("title"))
        if not has_name:
            img = a.find("img")
            if img and img.get("alt"):
                has_name = True

        if not has_name:
            issues.append({
                "rule_code": "link-name-missing",
                "issue_title": "Links need descriptive text",
                "description": "Some links do not communicate their destination because they lack text or an accessible name.",
                "severity": "serious",
                "wcag": "WCAG 2.4.4",
                "element": selector,
                "element_html": html_snippet,
                "recommendation": "Use meaningful link text that explains the destination or purpose of the link.",
            })
        elif link_text.lower() in vague_texts:
            issues.append({
                "rule_code": "link-text-vague",
                "issue_title": "Links have generic or ambiguous phrasing",
                "description": f"The link text '{link_text}' fails to inform users where the link leads when read out of context.",
                "severity": "minor",
                "wcag": "WCAG 2.4.4",
                "element": selector,
                "element_html": html_snippet,
                "recommendation": "Replace generic link text with specific text that describes the destination (e.g. 'Read accessibility guide').",
            })
        else:
            links_passed += 1

    if links and links_passed > 0:
        passed_checks += min(links_passed, 5)
    elif not links:
        passed_checks += 1

    # 7. Check: Headings structure (WCAG 1.3.1)
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    h1_list = soup.find_all("h1")

    if not h1_list:
        issues.append({
            "rule_code": "heading-h1-missing",
            "issue_title": "Page missing main <h1> heading",
            "description": "The page does not have a top-level <h1> heading to establish the primary topic.",
            "severity": "moderate",
            "wcag": "WCAG 1.3.1",
            "element": "<h1>",
            "element_html": "<body>",
            "recommendation": "Add a single, descriptive <h1> heading at the start of your main content area.",
        })
    elif len(h1_list) > 1:
        issues.append({
            "rule_code": "heading-h1-multiple",
            "issue_title": "Multiple <h1> headings found",
            "description": f"The page has {len(h1_list)} <h1> headings. A single <h1> per page provides a clearer document outline.",
            "severity": "minor",
            "wcag": "WCAG 1.3.1",
            "element": "<h1>",
            "element_html": truncate_html(h1_list[1]),
            "recommendation": "Reserve <h1> for the page's main title and use <h2> through <h6> for subsections.",
        })
    else:
        passed_checks += 2

    # Check for skipped heading levels
    last_level = 0
    skipped_found = False
    for h in headings:
        level = int(h.name[1])
        if last_level > 0 and level > last_level + 1 and not skipped_found:
            issues.append({
                "rule_code": "heading-skipped-level",
                "issue_title": f"Heading structure skips levels (h{last_level} to h{level})",
                "description": f"Headings should follow an ordered hierarchy. Skipping from <h{last_level}> to <h{level}> confuses screen reader navigation.",
                "severity": "moderate",
                "wcag": "WCAG 1.3.1",
                "element": build_selector(h),
                "element_html": truncate_html(h),
                "recommendation": f"Use an <h{last_level + 1}> heading instead of skipping directly to <h{level}>.",
            })
            skipped_found = True
        last_level = level

    if not skipped_found and headings:
        passed_checks += 1

    # 8. Check: Viewport zoom disabled (WCAG 1.4.4)
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    if viewport_meta:
        content = (viewport_meta.get("content") or "").lower()
        if "user-scalable=no" in content or "user-scalable=0" in content or "maximum-scale=1" in content:
            issues.append({
                "rule_code": "meta-viewport-zoom",
                "issue_title": "Zooming disabled in viewport meta tag",
                "description": "The viewport meta tag disables pinch-to-zoom, preventing low-vision users from scaling content.",
                "severity": "moderate",
                "wcag": "WCAG 1.4.4",
                "element": '<meta name="viewport">',
                "element_html": truncate_html(viewport_meta),
                "recommendation": "Remove user-scalable=no and allow maximum-scale of at least 2.0 or 5.0.",
            })
        else:
            passed_checks += 1
    else:
        passed_checks += 1

    # 9. Check: Landmarks <main> or role="main" (WCAG 2.4.1)
    main_landmark = soup.find(["main"]) or soup.find(attrs={"role": "main"})
    if not main_landmark:
        issues.append({
            "rule_code": "landmark-main-missing",
            "issue_title": "Page missing <main> landmark",
            "description": "No <main> landmark element found. Landmarks allow assistive tech users to jump past navigation directly to content.",
            "severity": "moderate",
            "wcag": "WCAG 2.4.1",
            "element": "<main>",
            "element_html": "<body>",
            "recommendation": "Wrap the primary content in a <main> element or add role=\"main\" to your content container.",
        })
    else:
        passed_checks += 1

    # 10. Check: Tables missing headers (WCAG 1.3.1)
    tables = soup.find_all("table")
    for tbl in tables:
        has_th = bool(tbl.find("th"))
        if not has_th and tbl.find("td"):
            issues.append({
                "rule_code": "table-missing-headers",
                "issue_title": "Data table missing header cells (<th>)",
                "description": "A table contains data cells without any header <th> cells to identify column or row headers.",
                "severity": "moderate",
                "wcag": "WCAG 1.3.1",
                "element": build_selector(tbl),
                "element_html": truncate_html(tbl),
                "recommendation": "Add <th> cells with scope=\"col\" or scope=\"row\" to define data headers.",
            })
        elif has_th:
            passed_checks += 1

    # 11. Check: Deprecated presentational elements (WCAG 4.1.1)
    deprecated = soup.find_all(["marquee", "blink", "font", "center", "strike"])
    for dep in deprecated:
        issues.append({
            "rule_code": f"deprecated-tag-{dep.name}",
            "issue_title": f"Deprecated <{dep.name}> tag used",
            "description": f"The <{dep.name}> tag is obsolete and can harm accessibility.",
            "severity": "minor",
            "wcag": "WCAG 4.1.1",
            "element": f"<{dep.name}>",
            "element_html": truncate_html(dep),
            "recommendation": f"Replace <{dep.name}> with semantic HTML elements and CSS styling.",
        })

    # 12. Check: Tabindex greater than 0 (WCAG 2.4.3)
    elements_with_tabindex = soup.find_all(attrs={"tabindex": True})
    for elem in elements_with_tabindex:
        try:
            val = int(elem.get("tabindex"))
            if val > 0:
                issues.append({
                    "rule_code": "tabindex-positive",
                    "issue_title": "Positive tabindex disrupts natural focus order",
                    "description": f"Element has tabindex=\"{val}\". Positive tabindex forces focus out of natural order.",
                    "severity": "moderate",
                    "wcag": "WCAG 2.4.3",
                    "element": build_selector(elem),
                    "element_html": truncate_html(elem),
                    "recommendation": "Avoid positive tabindex. Use tabindex=\"0\" or restructure the DOM to follow a logical tab order.",
                })
        except ValueError:
            pass

    # Calculate summary counts
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    serious_count = sum(1 for i in issues if i["severity"] == "serious")
    moderate_count = sum(1 for i in issues if i["severity"] == "moderate")
    minor_count = sum(1 for i in issues if i["severity"] == "minor")
    total_issues = len(issues)

    # Score calculation algorithm
    if total_issues == 0:
        score = 100
    else:
        deduction = (critical_count * 14) + (serious_count * 7) + (moderate_count * 3.5) + (minor_count * 1.5)
        score = max(15, min(98, round(100 - deduction)))

    # Ensure passed_checks is at least baseline
    passed_checks = max(passed_checks, 12 if total_issues > 0 else 35)

    summary = {
        "score": score,
        "total": total_issues,
        "critical": critical_count,
        "serious": serious_count,
        "moderate": moderate_count,
        "minor": minor_count,
        "passed": passed_checks,
    }

    # Format issues with 1-based sequential IDs for front-end rendering
    formatted_issues = []
    for idx, item in enumerate(issues, start=1):
        formatted_issues.append({
            "id": idx,
            "rule_code": item["rule_code"],
            "title": item["issue_title"],
            "description": item["description"],
            "severity": item["severity"].capitalize(),
            "raw_severity": item["severity"],
            "wcag": item["wcag"],
            "element": item["element"],
            "element_html": item["element_html"],
            "recommendation": item["recommendation"],
            "page_url": final_url,
        })

    return {
        "url": final_url,
        "summary": summary,
        "issues": formatted_issues,
    }
