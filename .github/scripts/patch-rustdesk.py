#!/usr/bin/env python3
"""Patch RustDesk source with custom server, key, password and permissions."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_RS = ROOT / "libs" / "hbb_common" / "src" / "config.rs"
PERM_PW_RS = ROOT / "libs" / "hbb_common" / "src" / "config" / "permanent_password.rs"

# Custom settings
ID_SERVER = "rd.tianxiacloud.cn"
RELAY_SERVER = "rd.tianxiacloud.cn"
KEY = "2EtrIsxRFOzSD01KPUVgSv+mDqGAPXmJzfl40HR4WLM="
PASSWORD = "Summer521."


def patch_config_rs():
    text = CONFIG_RS.read_text(encoding="utf-8")

    # 1. Replace default rendezvous server and public key
    text = re.sub(
        r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]+\];',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{ID_SERVER}"];',
        text,
    )
    text = re.sub(
        r'pub const RS_PUB_KEY: &str = "[^"]+";',
        f'pub const RS_PUB_KEY: &str = "{KEY}";',
        text,
    )

    # 2. Inject default options into Config2::load()
    options_block = (
        '\n'
        '        // --- custom defaults begin ---\n'
        '        let default_options = [\n'
        f'            ("custom-rendezvous-server", "{ID_SERVER}"),\n'
        f'            ("relay-server", "{RELAY_SERVER}"),\n'
        f'            ("key", "{KEY}"),\n'
        '            ("verification-method", "use-permanent-password"),\n'
        '            ("approve-mode", "password"),\n'
        '            ("disable-change-permanent-password", "Y"),\n'
        '            ("disable-change-id", "Y"),\n'
        '        ];\n'
        '        for (k, v) in default_options {\n'
        '            if !config.options.contains_key(k) {\n'
        '                config.options.insert(k.to_string(), v.to_string());\n'
        '                store = true;\n'
        '            }\n'
        '        }\n'
        '        // --- custom defaults end ---\n'
    )

    config2_load_end = re.search(
        r'(\s+if store \{\n\s+config\.store\(\);\n\s+\}\n\s+config\n\s+\}\n\s+pub fn file\(\) -> PathBuf \{)',
        text,
    )
    if not config2_load_end:
        raise RuntimeError("Could not locate Config2::load() injection point")
    insert_pos = config2_load_end.start()
    text = text[:insert_pos] + options_block + "\n" + text[insert_pos:]

    # 3. Inject default permanent password into Config::load()
    password_block = (
        '\n'
        '        // --- custom default password begin ---\n'
        '        if config.password.is_empty() {\n'
        '            config.salt = Config::get_auto_password(DEFAULT_SALT_LEN);\n'
        f'            if let Some(stored) = encode_permanent_password_encrypted_storage_from_h1(\n'
        f'                &compute_permanent_password_h1("{PASSWORD}", &config.salt)\n'
        '            ) {\n'
        '                config.password = stored;\n'
        '                store = true;\n'
        '            }\n'
        '        }\n'
        '        // --- custom default password end ---\n'
    )

    config_load_inject = re.search(
        r'(\s+if let Err\(err\) = Self::validate_or_decrypt_permanent_password_storage\(&mut config\) \{\n\s+log::error!\([^)]+\);\n\s+\}\n)',
        text,
    )
    if not config_load_inject:
        raise RuntimeError("Could not locate Config::load() injection point")
    insert_pos = config_load_inject.end()
    text = text[:insert_pos] + password_block + text[insert_pos:]

    CONFIG_RS.write_text(text, encoding="utf-8")
    print(f"Patched {CONFIG_RS}")


def patch_permanent_password_rs():
    text = PERM_PW_RS.read_text(encoding="utf-8")
    # Make the encoder public so config.rs can call it during Config::load().
    text = text.replace(
        "pub(super) fn encode_permanent_password_encrypted_storage_from_h1(",
        "pub fn encode_permanent_password_encrypted_storage_from_h1(",
    )
    PERM_PW_RS.write_text(text, encoding="utf-8")
    print(f"Patched {PERM_PW_RS}")


if __name__ == "__main__":
    patch_permanent_password_rs()
    patch_config_rs()
    print("All patches applied.")
