#!/usr/bin/env python3
"""Import a local Markdown file as a Feishu Docx cloud document, then DM the link.

Flow:
  local .md
    -> upload media           (drive/v1/medias/upload_all, parent_type=ccm_import_open)
    -> create import task      (drive/v1/import_tasks, type=docx)
    -> poll task               (drive/v1/import_tasks/{ticket})
    -> send interactive card   (im/v1/messages?receive_id_type=email)

Credentials & defaults come from env (or a .env next to this skill):
  FEISHU_APP_ID       (required)
  FEISHU_APP_SECRET   (required)
  FEISHU_TO_EMAIL     default recipient email (override with --to)
  FEISHU_FOLDER_TOKEN target Drive folder (optional; defaults to My Space root)
  FEISHU_BASE         default https://open.feishu.cn  (use open.larksuite.com for Lark Intl)
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


def load_dotenv():
    """Load KEY=VALUE lines from .env in the skill dir or cwd (does not override real env)."""
    for candidate in (Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def die(msg):
    sys.exit(f"✗ {msg}")


def check(resp, what):
    try:
        data = resp.json()
    except ValueError:
        die(f"{what}: non-JSON response (HTTP {resp.status_code}): {resp.text[:300]}")
    if data.get("code") not in (0, None):
        die(f"{what} failed [code {data.get('code')}]: {data.get('msg')}")
    return data


def get_token(base, app_id, app_secret):
    r = requests.post(
        f"{base}/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=30,
    )
    data = check(r, "Get tenant_access_token")
    tok = data.get("tenant_access_token")
    if not tok:
        die(f"No tenant_access_token in response: {data}")
    return tok


def upload_media(base, token, path):
    size = path.stat().st_size
    with path.open("rb") as fh:
        r = requests.post(
            f"{base}/open-apis/drive/v1/medias/upload_all",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "file_name": path.name,
                "parent_type": "ccm_import_open",
                "parent_node": "",
                "size": str(size),
                "extra": json.dumps({"obj_type": "docx", "file_extension": "md"}),
            },
            files={"file": (path.name, fh, "text/markdown")},
            timeout=120,
        )
    return check(r, "Upload media")["data"]["file_token"]


def root_folder_token(base, token):
    r = requests.get(
        f"{base}/open-apis/drive/explorer/v2/root_folder/meta",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return check(r, "Get root folder")["data"]["token"]


def list_folder(base, token, folder_token):
    """Yield all direct children {token, name, type, url} of a Drive folder."""
    page_token = None
    while True:
        params = {"folder_token": folder_token, "page_size": 200}
        if page_token:
            params["page_token"] = page_token
        r = requests.get(
            f"{base}/open-apis/drive/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        data = check(r, "List folder")["data"]
        for f in data.get("files", []):
            yield f
        if not data.get("has_more"):
            break
        page_token = data.get("next_page_token")


def find_or_create_folder(base, token, name, parent_token):
    for f in list_folder(base, token, parent_token):
        if f.get("type") == "folder" and f.get("name") == name:
            return f["token"]
    r = requests.post(
        f"{base}/open-apis/drive/v1/files/create_folder",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": name, "folder_token": parent_token},
        timeout=30,
    )
    return check(r, "Create folder")["data"]["token"]


def delete_file(base, token, file_token, file_type="docx"):
    r = requests.delete(
        f"{base}/open-apis/drive/v1/files/{file_token}",
        headers={"Authorization": f"Bearer {token}"},
        params={"type": file_type},
        timeout=30,
    )
    check(r, "Delete file")


def add_member(base, token, doc_token, member_type, member_id, perm):
    """Grant a collaborator perm on a docx. perm: view | edit | full_access (可管理)."""
    r = requests.post(
        f"{base}/open-apis/drive/v1/permissions/{doc_token}/members",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"type": "docx"},
        json={"member_type": member_type, "member_id": member_id, "perm": perm},
        timeout=30,
    )
    check(r, "Add collaborator")


def create_import(base, token, file_token, title, folder_token):
    body = {
        "file_extension": "md",
        "file_token": file_token,
        "type": "docx",
        "file_name": title,
        "point": {"mount_type": 1, "mount_key": folder_token},
    }
    r = requests.post(
        f"{base}/open-apis/drive/v1/import_tasks",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    return check(r, "Create import task")["data"]["ticket"]


def poll_import(base, token, ticket, tries=40, delay=1.5):
    for _ in range(tries):
        r = requests.get(
            f"{base}/open-apis/drive/v1/import_tasks/{ticket}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        result = check(r, "Poll import task")["data"]["result"]
        status = result.get("job_status")
        # 0 = success. 1/2 = initializing/processing. anything else = error.
        if status == 0 and result.get("url"):
            return result["url"], result.get("token")
        if status not in (0, 1, 2):
            die(f"Import failed [job_status {status}]: {result.get('job_error_msg')}")
        time.sleep(delay)
    die("Import task timed out (still processing).")


def resolve_open_id_by_mobile(base, token, mobile):
    r = requests.post(
        f"{base}/open-apis/contact/v3/users/batch_get_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"user_id_type": "open_id"},
        json={"mobiles": [mobile]},
        timeout=30,
    )
    users = check(r, "Resolve mobile -> open_id")["data"].get("user_list", [])
    for u in users:
        if u.get("user_id"):
            return u["user_id"]
    die(f"No Feishu user found for mobile {mobile} (not in org, or not in app scope).")


def send_card(base, token, receive_id_type, receive_id, title, url):
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "📄 新文档已生成"}},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**{title}**\n已导入为飞书云文档"}},
            {"tag": "action", "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "打开文档"},
                "type": "primary",
                "url": url,
            }]},
        ],
    }
    r = requests.post(
        f"{base}/open-apis/im/v1/messages",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"receive_id_type": receive_id_type},
        json={"receive_id": receive_id, "msg_type": "interactive", "content": json.dumps(card)},
        timeout=30,
    )
    check(r, "Send message")


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="Import a .md as a Feishu doc and DM the link.")
    ap.add_argument("markdown", help="Path to the .md file")
    ap.add_argument("--to", default=os.environ.get("FEISHU_TO_EMAIL"), help="Recipient Feishu email")
    ap.add_argument("--open-id", dest="open_id", default=os.environ.get("FEISHU_TO_OPEN_ID"), help="Recipient open_id (ou_...)")
    ap.add_argument("--mobile", default=os.environ.get("FEISHU_TO_MOBILE"), help="Recipient mobile (e.g. +8613800138000); needs contact:user.id:readonly")
    ap.add_argument("--title", help="Document title (defaults to file stem)")
    ap.add_argument("--folder", default=os.environ.get("FEISHU_FOLDER_TOKEN"), help="Target Drive folder_token")
    ap.add_argument("--folder-name", dest="folder_name", default=os.environ.get("FEISHU_FOLDER_NAME"),
                    help="Target folder by name under My Space root (created if missing), e.g. PaperSuggess")
    ap.add_argument("--no-send", action="store_true", help="Only create the doc, don't DM")
    ap.add_argument("--grant", choices=["view", "edit", "full_access"],
                    default=os.environ.get("FEISHU_GRANT_PERM"),
                    help="Add the recipient as a collaborator (full_access = 可管理/admin)")
    args = ap.parse_args()

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        die("Set FEISHU_APP_ID and FEISHU_APP_SECRET (env or .env).")

    path = Path(args.markdown).expanduser()
    if not path.is_file():
        die(f"File not found: {path}")
    title = args.title or path.stem
    base = os.environ.get("FEISHU_BASE", "https://open.feishu.cn").rstrip("/")

    token = get_token(base, app_id, app_secret)
    print("• got tenant_access_token")

    folder = args.folder
    if not folder and args.folder_name:
        folder = find_or_create_folder(base, token, args.folder_name, root_folder_token(base, token))
        print(f"• folder '{args.folder_name}' -> {folder}")
    if not folder:
        folder = root_folder_token(base, token)
    file_token = upload_media(base, token, path)
    print(f"• uploaded media ({path.name})")

    ticket = create_import(base, token, file_token, title, folder)
    print(f"• import task created (ticket {ticket})")

    url, doc_token = poll_import(base, token, ticket)
    print(f"✓ document ready: {url}")

    # Resolve recipient once (used for both --grant and the DM).
    if args.open_id:
        member_type, send_type, rid = "openid", "open_id", args.open_id
    elif args.to:
        member_type, send_type, rid = "email", "email", args.to
    elif args.mobile:
        rid = resolve_open_id_by_mobile(base, token, args.mobile)
        member_type, send_type = "openid", "open_id"
    else:
        member_type = send_type = rid = None

    if args.grant:
        if not rid:
            die("--grant needs a recipient (--open-id / --to / --mobile).")
        add_member(base, token, doc_token, member_type, rid, args.grant)
        print(f"✓ granted {args.grant} to {rid}")

    if args.no_send:
        return
    if not rid:
        die("No recipient. Pass --open-id / --to <email> / --mobile <number> "
            "or set FEISHU_TO_OPEN_ID / FEISHU_TO_EMAIL / FEISHU_TO_MOBILE.")
    send_card(base, token, send_type, rid, title, url)
    print(f"✓ pushed to {rid}")


if __name__ == "__main__":
    main()
