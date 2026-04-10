import re
import time
import subprocess

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app.settings import ROUTER_USERNAME, ROUTER_PASSWORD


def is_valid_ipv4(ip: str) -> bool:
    if not ip:
        return False
    ip = ip.strip()
    if not re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split("."))


def get_ethernet_gateway() -> str | None:
    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        text = result.stdout or ""
        patterns = [
            r"Puerta de enlace predeterminada[ .:]+(\d{1,3}(?:\.\d{1,3}){3})",
            r"Default Gateway[ .:]+(\d{1,3}(?:\.\d{1,3}){3})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                ip = match.group(1).strip()
                if is_valid_ipv4(ip):
                    return ip
    except Exception:
        pass
    return None


def login_router():
    router_ip = get_ethernet_gateway()
    if not router_ip:
        return False, "No se pudo detectar la IP del router."

    url = f"http://{router_ip}"
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        time.sleep(1)

        inputs = driver.find_elements(By.TAG_NAME, "input")
        user_input = None
        pass_input = None
        debug = []

        for el in inputs:
            try:
                rect    = driver.execute_script(
                    "const r = arguments[0].getBoundingClientRect(); return {w:r.width,h:r.height};", el
                )
                el_type = (el.get_attribute("type") or "").lower()
                el_name = (el.get_attribute("name") or "").lower()
                el_id   = (el.get_attribute("id")   or "").lower()
                visible = el.is_displayed() and rect["w"] > 0 and rect["h"] > 0

                debug.append(f"type={el_type} name={el_name} id={el_id} visible={visible}")

                if not visible:
                    continue
                if pass_input is None and el_type == "password":
                    pass_input = el
                    continue
                if user_input is None and (
                    el_type in ("text", "email") or el_name == "username" or el_id == "username"
                ):
                    user_input = el
            except Exception:
                pass

        if not user_input or not pass_input:
            return False, "No encontré inputs reales.\n" + "\n".join(debug)

        driver.execute_script(
            """
            arguments[0].focus();
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
            arguments[2].focus();
            arguments[2].value = arguments[3];
            arguments[2].dispatchEvent(new Event('input',  {bubbles:true}));
            arguments[2].dispatchEvent(new Event('change', {bubbles:true}));
            """,
            user_input, str(ROUTER_USERNAME),
            pass_input, str(ROUTER_PASSWORD),
        )

        current_user = driver.execute_script("return arguments[0].value;", user_input) or ""
        current_pass = driver.execute_script("return arguments[0].value;", pass_input) or ""

        if current_user != str(ROUTER_USERNAME) or current_pass != str(ROUTER_PASSWORD):
            return False, (
                f"No se escribieron las credenciales. user='{current_user}' pass_len={len(current_pass)}\n"
                + "\n".join(debug)
            )

        driver.execute_script(
            """
            const el = arguments[0];
            el.focus();
            ["keydown","keypress","keyup"].forEach(type => {
                el.dispatchEvent(new KeyboardEvent(type, {
                    bubbles:true, cancelable:true,
                    key:'Enter', code:'Enter', keyCode:13, which:13
                }));
            });
            """,
            pass_input,
        )

        time.sleep(1)
        return True, f"Login intentado en {url}"

    except Exception as e:
        return False, f"Error al abrir o loguear en el router: {e}"
    # driver se mantiene abierto intencionalmente para que el usuario lo use
