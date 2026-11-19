# Review Notulen (Human-in-the-Loop) — Rencana Implementasi Backend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hasil AI menjadi draft yang hanya bisa dilihat dan diedit organizer, lalu dikirim ke peserta sebagai versi bernomor saat organizer klik Publikasikan atau Kirim ulang.

**Architecture:** Status editorial disimpan di `meetings.notulen_status`, terpisah dari status pipeline di `Recording`. Logika review dikumpulkan di modul baru `services/notulen.py` + `routers/notulen.py`. Satu fungsi `is_notulen_visible()` menjadi gerbang untuk setiap jalur baca peserta. Pengiriman email dipindah dari pipeline ke Celery task `send_notulen_task` yang dipanggil saat publish atau kirim ulang.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Celery, pytest.

**Spec:** [`docs/notulen-review-design.md`](./notulen-review-design.md). Bentuk request/response persis ada di [`docs/notulen-review-frontend-handoff.md`](./notulen-review-frontend-handoff.md) bagian 2–3. Kalau plan ini dan handoff berbeda, **handoff yang benar** (Helena membangun FE dari situ).

## Global Constraints

- Branch: `feature/backend-notulen-review` dari `main`.
- Tidak ada setting `.env` baru di fitur ini. Domain Message-ID diambil dari `SMTP_USER`.
- Kolom enum PostgreSQL di migrasi wajib memakai pola di CLAUDE.md: `postgresql.ENUM(...).create(bind, checkfirst=True)` di awal `upgrade()`, lalu `postgresql.ENUM(..., create_type=False)` di kolom.
- Semua error memakai `{"detail": "..."}` dengan pesan Bahasa Indonesia, persis seperti yang ditulis di plan ini.
- Folder `ml/` tidak diubah. Signature fungsi ML *frozen*.
- Jalankan satu file test: `docker compose exec backend-api pytest tests/<file>.py -v`. Seluruh suite: `make test`.
- Celery task di-import **lazy** (di dalam fungsi) dari service, mengikuti pola `upload_recording()`, supaya test bisa me-monkeypatch `.delay`.

## Review Focus

1. **Assignee mengubah status action item draft** lewat `PATCH /action-items/{id}` atau portal check-in → harus 404, bukan bocor. Test ada di Task 4.
2. **Tombol Kirim ulang diklik dua kali** → request kedua 409, hanya satu versi baru dan satu batch email. Test ada di Task 6.
3. **Rename speaker dengan label yang tidak ada atau nama baru kosong** → 400 atau 422, transkrip tidak berubah. Test ada di Task 5.
4. **Edit keputusan atau topik berisi item kosong atau spasi saja** → di-strip dan dibuang; `tldr` kosong → 422. Test ada di Task 5.
5. **Backfill meeting yang punya summary tapi tanpa action item** → `content.action_items` berupa `[]`, bukan `null`; meeting tanpa summary tetap `notulen_status = null`. Dicek manual dengan SQL di Task 1, karena migrasi berjalan sebelum test.

---

### Task 1: Model data, migrasi, backfill

**Files:**
- Modify: `backend/app/models/meeting.py` (enum `NotulenStatus`, dua kolom, relasi)
- Create: `backend/app/models/notulen_version.py`
- Modify: `backend/app/models/action_item.py` (dua kolom)
- Modify: `backend/app/models/__init__.py` (daftarkan `NotulenVersion`)
- Create: `backend/alembic/versions/b4c5d6e7f8a9_add_notulen_review.py` (`down_revision = "a3b4c5d6e7f8"`)
- Modify: `backend/tests/conftest.py` (fixture `make_meeting`)
- Test: `backend/tests/test_notulen_models.py`

**Interfaces:**
- Produces:
  - `NotulenStatus(str, enum.Enum)`: `draft`, `published` di `app.models.meeting`
  - `Meeting.notulen_status: NotulenStatus | None`, `Meeting.notulen_edited_at: datetime | None`, `Meeting.notulen_versions: list[NotulenVersion]` (cascade `all, delete-orphan`)
  - `NotulenVersionKind(str, enum.Enum)`: `ai`, `published`; `NotulenVersion(id, meeting_id, kind, version: int | None, content: dict, created_by: UUID | None, created_at)` dengan `UniqueConstraint("meeting_id", "version", name="uq_notulen_versions_meeting_version")`
  - `ActionItem.ai_assignee_text: str | None`, `ActionItem.ai_due_date_text: str | None`
  - Fixture `make_meeting(organizer: User, members: list[User] = (), *, notulen_status: NotulenStatus | None = None, with_notulen: bool = False, with_recording: bool = False) -> Meeting`:
    - `scheduled_at` = sekarang + 1 hari, judul `"Team Sync"`.
    - Organizer menjadi participant `role=organizer`. Setiap member menjadi participant `role=peserta` dengan `Invitation(token=uuid4().hex, expires_at=now+30 hari)`.
    - `with_notulen` membuat `Summary(tldr="Ringkasan AI", decisions=["Keputusan A"], topics=["Topik A"])`, `Transcript(segments=[{"speaker": "SPEAKER_00", "start": 0.0, "end": 5.0, "text": "Halo semua"}])`, dan satu `ActionItem(task="Kirim laporan", source=ai)` yang di-assign ke member pertama.
    - `with_recording` membuat `Recording(file_url="meetings/x.mp3", size=1, processing_status=completed)`.

- [ ] **Step 1: Tulis test yang gagal** di `test_notulen_models.py`
  - `test_published_version_number_unique_per_meeting`: dua `NotulenVersion(kind=published, version=1)` untuk meeting yang sama → `db_session.commit()` melempar `IntegrityError`.
  - `test_multiple_ai_snapshots_allowed`: dua `NotulenVersion(kind=ai, version=None)` untuk meeting yang sama → commit berhasil, `len(meeting.notulen_versions) == 2`.
  - `test_deleting_meeting_cascades_versions`: hapus meeting → `db_session.query(NotulenVersion).count() == 0`.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_models.py -v`
  Expected: FAIL, `ImportError` untuk `NotulenVersion`.

- [ ] **Step 3: Implementasi model dan fixture** sesuai Interfaces.

- [ ] **Step 4: Tulis migrasi** `b4c5d6e7f8a9_add_notulen_review.py`
  - Buat tipe `notulenstatus` dan `notulenversionkind` dengan pola enum CLAUDE.md.
  - Tambah kolom `meetings.notulen_status`, `meetings.notulen_edited_at`, `action_items.ai_assignee_text`, `action_items.ai_due_date_text`.
  - Buat tabel `notulen_versions` dengan index di `meeting_id`.
  - Backfill (keputusan #13), persis seperti ini:

  ```sql
  UPDATE meetings SET notulen_status = 'published'
  WHERE id IN (SELECT meeting_id FROM summaries);

  INSERT INTO notulen_versions (id, meeting_id, kind, version, content, created_by, created_at)
  SELECT gen_random_uuid(), s.meeting_id, 'published', 1,
    jsonb_build_object(
      'tldr', s.tldr, 'decisions', s.decisions, 'topics', s.topics,
      'action_items', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
          'id', ai.id::text, 'task', ai.task,
          'assignee_participant_id', ai.assignee_participant_id::text,
          'assignee_name', COALESCE(u.name, mp.email),
          'due_date', ai.due_date::text) ORDER BY ai.id)
        FROM action_items ai
        LEFT JOIN meeting_participants mp ON mp.id = ai.assignee_participant_id
        LEFT JOIN users u ON u.id = mp.user_id
        WHERE ai.meeting_id = s.meeting_id), '[]'::jsonb)),
    m.organizer_id, now()
  FROM summaries s JOIN meetings m ON m.id = s.meeting_id;
  ```

  - `downgrade()` menghapus tabel, kolom, lalu kedua tipe enum.

- [ ] **Step 5: Terapkan migrasi dan jalankan test**
  Run: `make migrate && docker compose exec backend-api pytest tests/test_notulen_models.py -v`
  Expected: PASS (3 test).

- [ ] **Step 6: Cek backfill di database dev** (Review Focus #5)
  Run: `docker compose exec postgres psql -U meetmate -d meetmate -c "SELECT count(*) FROM notulen_versions WHERE jsonb_typeof(content->'action_items') <> 'array';" -c "SELECT count(*) FROM meetings m WHERE notulen_status IS NOT NULL AND NOT EXISTS (SELECT 1 FROM summaries s WHERE s.meeting_id = m.id);"`
  Expected: kedua hasil `0`.

- [ ] **Step 7: Commit**
  `git commit -m "feat(notulen): add notulen status, versions table, and AI review columns"`

---

### Task 2: Simpan hasil AI sebagai draft, pipeline berhenti mengirim email

**Files:**
- Create: `backend/app/services/notulen.py`
- Create: `backend/app/schemas/notulen.py`
- Modify: `backend/app/tasks/process_recording.py` (step 8, hapus step 10, ubah status akhir)
- Modify: `CLAUDE.md` (bagian "Data Flow for Recording Processing": langkah 5 menjadi "Notulen disimpan sebagai draft; email dikirim saat organizer publish", dan urutan `ProcessingStatus` tanpa `sending_email`)
- Test: `backend/tests/test_notulen_service.py`

**Interfaces:**
- Consumes: model dan fixture dari Task 1.
- Produces (di `app.services.notulen`):
  - `is_notulen_visible(meeting: Meeting, user_id: uuid.UUID | None) -> bool`: `True` kalau `user_id == meeting.organizer_id` atau `meeting.notulen_status == NotulenStatus.published`.
  - `needs_review(item: ActionItem) -> bool`
  - `build_notulen_meta(meeting: Meeting) -> NotulenMeta`
  - `mark_edited(meeting: Meeting) -> None`: set `notulen_edited_at = datetime.now(timezone.utc)`, tanpa commit.
  - `save_ai_results(db: Session, meeting: Meeting, participants: list[MeetingParticipant], summary_result, action_items_result) -> Summary`. Tanpa commit; caller yang commit. `summary_result` punya atribut `tldr`, `decisions`, `topics`. Setiap item `action_items_result` punya atribut `task`, `assignee_name`, `due_date_text`.
- Produces (di `app.schemas.notulen`): `NotulenMeta(status: Literal["draft", "published"] | None, current_version: int | None, last_published_at: datetime | None, edited_at: datetime | None, has_unsent_changes: bool, needs_review_count: int)`.

Perilaku `save_ai_results`:
1. Hapus `Summary` dan action item `source=ai` milik meeting. Action item manual tetap.
2. Buat `Summary` baru.
3. Untuk setiap action item: cocokkan `assignee_name` ke nama peserta dengan cara yang sama seperti kode lama (`p.user.name if p.user else p.email`). Kalau tidak cocok dan nilainya tidak kosong, isi `ai_assignee_text`. Parse `due_date_text` dengan `date.fromisoformat(text.strip())`. Kalau gagal dan nilainya tidak kosong, isi `ai_due_date_text`.
4. Tambah `NotulenVersion(kind=ai, version=None, created_by=None)` dengan `content` berbentuk snapshot `ai` dari spec.
5. Set `meeting.notulen_status = draft` dan `meeting.notulen_edited_at = None`.

- [ ] **Step 1: Tulis test yang gagal.** Test memakai `types.SimpleNamespace` sebagai pengganti output ML, karena container backend-api tidak punya folder `ml/`.
  - `test_save_ai_results_creates_draft_and_ai_snapshot`: setelah dipanggil dan commit → `meeting.notulen_status == NotulenStatus.draft`; tepat satu `NotulenVersion` dengan `kind == ai` dan `version is None`; `content["action_items"][0] == {"task": "Siapkan anggaran", "assignee_name": "Pak Budi", "due_date_text": "Jumat depan"}`.
  - `test_unmatched_ai_values_are_kept_for_review`: action item yang sama → `assignee_participant_id is None`, `ai_assignee_text == "Pak Budi"`, `ai_due_date_text == "Jumat depan"`, `needs_review(item) is True`.
  - `test_matched_ai_values_leave_no_review_flag`: member diberi `name="Budi Santoso"`, AI memberi `assignee_name="Budi Santoso"`, `due_date_text="2026-12-01"` → assignee terisi, `due_date == date(2026, 12, 1)`, kedua kolom `ai_*` bernilai `None`, `needs_review(item) is False`.
  - `test_save_ai_results_keeps_manual_action_items`: action item `source=manual` yang sudah ada tetap ada.
  - `test_has_unsent_changes_only_after_edit_post_publish`: published v1 dibuat pada `t0` → `False` saat `edited_at` None; `True` saat `edited_at = t0 + 1 menit`; `False` saat status `draft` meskipun `edited_at` terisi.
  - `test_is_notulen_visible`: organizer `True` saat draft; member `False` saat draft dan `True` saat published.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_service.py -v`
  Expected: FAIL, `ModuleNotFoundError: app.services.notulen`.

- [ ] **Step 3: Implementasi `services/notulen.py` dan `schemas/notulen.py`** sesuai Interfaces.

- [ ] **Step 4: Ubah `process_recording.py`**
  - Step 8 tetap menghapus dan membuat `Transcript`, lalu memanggil `notulen_service.save_ai_results(...)` sebagai pengganti pembuatan `Summary` dan `ActionItem`.
  - Hapus step 10 (PDF + email) beserta import `send_notulen_email` dan `generate_notulen_pdf`.
  - Step 11 (kunci absensi, `meeting.status = completed`) tetap, diakhiri dengan `_set_step(db, recording, "extract", ProcessingStatus.completed)`.

- [ ] **Step 5: Jalankan test**
  Run: `docker compose exec backend-api pytest tests/test_notulen_service.py -v`
  Expected: PASS (6 test).

- [ ] **Step 6: Verifikasi manual pipeline.** Rebuild dan restart `celery-worker`, upload satu audio pendek dari UI.
  Expected: status rekaman menjadi `completed`, **tidak ada** email baru di Mailhog (http://localhost:8025), `SELECT notulen_status FROM meetings WHERE id = '<id>'` bernilai `draft`.

- [ ] **Step 7: Commit**
  `git commit -m "feat(notulen): save AI output as draft and stop auto-sending notulen email"`

---

### Task 3: Sembunyikan draft di detail meeting, PDF, pencarian, dan list

**Files:**
- Modify: `backend/app/schemas/meeting.py` (`MeetingDetail.notulen`, field review di dict action item, `MeetingListItem.notulen_status`)
- Modify: `backend/app/routers/meetings.py` (redaksi di semua respons `MeetingDetail`, gerbang `notulen.pdf`)
- Modify: `backend/app/services/meeting.py` (`search_meetings`)
- Test: `backend/tests/test_notulen_visibility.py`

**Interfaces:**
- Consumes: `is_notulen_visible`, `needs_review`, `build_notulen_meta` (Task 2).
- Produces:
  - `MeetingDetail.notulen: NotulenMeta`
  - Setiap action item di `MeetingDetail.action_items` mendapat `ai_assignee_text`, `ai_due_date_text`, `needs_review`.
  - `MeetingListItem.notulen_status: str | None`
  - Helper router `_hide_notulen_if_needed(meeting: Meeting, detail: MeetingDetail, user_id: uuid.UUID) -> MeetingDetail`. Kalau tidak terlihat: set `summary = None`, `transcript = None`, `action_items = []`. Dipakai di **semua** endpoint yang mengembalikan `MeetingDetail`: `GET /{id}`, `PATCH /{id}`, `PATCH /{id}/complete`, `PATCH /{id}/rsvp`, dan `POST /`.

Pencarian: kecocokan di `Summary.tldr` atau `ActionItem.task` hanya dihitung kalau `Meeting.notulen_status == published` atau `Meeting.organizer_id == user_id`. Kecocokan di `Meeting.title` tetap berlaku untuk semua.

- [ ] **Step 1: Tulis test yang gagal**
  - `test_member_gets_no_notulen_content_while_draft`: `GET /api/v1/meetings/{id}` sebagai member → `summary is None`, `transcript is None`, `action_items == []`, `notulen["status"] == "draft"`.
  - `test_organizer_sees_draft_with_review_fields`: sebagai organizer → `summary["tldr"] == "Ringkasan AI"`, dan `action_items[0]` punya key `needs_review`, `ai_assignee_text`, `ai_due_date_text`.
  - `test_member_sees_notulen_after_publish`: `notulen_status=published` → `summary` tidak `None`.
  - `test_rsvp_response_hides_draft`: `PATCH /api/v1/meetings/{id}/rsvp` sebagai member dengan `{"response": "akan_hadir"}` → `summary is None`.
  - `test_member_pdf_404_while_draft`: `GET /api/v1/meetings/{id}/notulen.pdf` sebagai member → 404, `detail == "Notulen belum tersedia"`.
  - `test_search_ignores_draft_content_for_member`: `GET /api/v1/meetings/search?q=Ringkasan` → member `total == 0`, organizer `total == 1`.
  - `test_list_item_exposes_notulen_status`: `GET /api/v1/meetings/` sebagai member → `items[0]["notulen_status"] == "draft"`.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_visibility.py -v`
  Expected: FAIL, isi `summary` masih terlihat oleh member.

- [ ] **Step 3: Implementasi** sesuai Interfaces.

- [ ] **Step 4: Jalankan test file ini dan suite lama yang menyentuh meeting**
  Run: `docker compose exec backend-api pytest tests/test_notulen_visibility.py tests/test_soft_delete.py tests/test_rsvp.py tests/test_meeting_content_access.py -v`
  Expected: PASS semua.

- [ ] **Step 5: Commit**
  `git commit -m "feat(notulen): hide draft notulen from participants in detail, PDF, search"`

---

### Task 4: Sembunyikan draft di portal check-in, action item saya, dan reminder

**Files:**
- Modify: `backend/app/services/checkin.py` (`get_checkin_info`, `get_checkin_notulen_pdf`, `update_checkin_action_item`)
- Modify: `backend/app/schemas/checkin.py` (`CheckinPageResponse.notulen: NotulenMeta | None`)
- Modify: `backend/app/services/action_item.py` (`get_my_action_items`, `update_action_item`)
- Modify: `backend/app/tasks/action_item_reminders.py`
- Test: `backend/tests/test_notulen_visibility_portal.py`

**Interfaces:**
- Consumes: `is_notulen_visible`, `build_notulen_meta` (Task 2); fixture `make_meeting` (token ada di `participant.invitation.token`).
- Produces: `CheckinPageResponse.notulen`. Di portal, visibilitas dicek dengan `is_notulen_visible(meeting, participant.user_id)`.

Aturan:
- `get_checkin_info`: kalau tidak terlihat → `summary = None`, `action_items = []`.
- `get_checkin_notulen_pdf` dan `update_checkin_action_item`: kalau tidak terlihat → 404 dengan pesan yang sama seperti kasus "tidak ditemukan" yang sudah ada.
- `get_my_action_items`: join `Meeting`, filter `Meeting.notulen_status == published`.
- `update_action_item`: kalau user bukan organizer dan notulen tidak terlihat → 404 `"Action item not found"` (pesan yang sama dengan item tidak ada, supaya keberadaan item tidak bocor).
- Reminder: join `Meeting`, filter `Meeting.notulen_status == published`.

- [ ] **Step 1: Tulis test yang gagal**
  - `test_checkin_info_hides_draft`: `GET /api/v1/check-in/{token}` → `summary is None`, `action_items == []`, `notulen["status"] == "draft"`.
  - `test_checkin_action_item_update_404_while_draft`: `PATCH /api/v1/check-in/{token}/action-items/{item_id}` dengan `{"status": "done"}` → 404 (Review Focus #1).
  - `test_checkin_pdf_404_while_draft`.
  - `test_my_action_items_excludes_draft_meetings`: `GET /api/v1/me/action-items` sebagai member → `items == []` saat draft, 1 item setelah status di-set `published`.
  - `test_assignee_cannot_patch_status_while_draft`: `PATCH /api/v1/action-items/{id}` sebagai member dengan `{"status": "done"}` → 404 (Review Focus #1).
  - `test_reminder_skips_draft_meetings`: action item ber-`due_date` besok; monkeypatch `app.tasks.action_item_reminders.send_action_item_reminder_email` untuk mencatat panggilan; jalankan `send_action_item_reminders_task()` → 0 panggilan saat draft, 1 panggilan saat published.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_visibility_portal.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implementasi** sesuai aturan.

- [ ] **Step 4: Jalankan test**
  Run: `docker compose exec backend-api pytest tests/test_notulen_visibility_portal.py -v`
  Expected: PASS (6 test).

- [ ] **Step 5: Commit**
  `git commit -m "feat(notulen): hide draft notulen in check-in portal, my action items, reminders"`

---

### Task 5: Endpoint edit (ringkasan, speaker, action item)

**Files:**
- Modify: `backend/app/schemas/notulen.py` (`SummaryUpdateRequest`, `SummaryResponse`, `SpeakerRenameRequest`, `TranscriptResponse`)
- Modify: `backend/app/services/notulen.py` (`get_organizer_meeting`, `update_summary`, `rename_speakers`)
- Create: `backend/app/routers/notulen.py`; Modify: `backend/app/main.py` (`app.include_router(notulen.router, prefix="/api/v1/meetings")`)
- Modify: `backend/app/schemas/action_item.py`, `backend/app/services/action_item.py`, `backend/app/routers/action_items.py`
- Test: `backend/tests/test_notulen_edit.py`

**Interfaces:**
- Consumes: `mark_edited` (Task 2).
- Produces:
  - `get_organizer_meeting(db, meeting_id, user_id) -> Meeting`: 404 `"Meeting not found"`, atau 403 `"Hanya organizer yang bisa mengedit notulen"`.
  - `update_summary(db, meeting_id, user_id, data: SummaryUpdateRequest) -> Summary`: partial; 404 `"Notulen belum tersedia"` kalau belum ada summary; memanggil `mark_edited`.
  - `rename_speakers(db, meeting_id, user_id, renames: dict[str, str]) -> Transcript`: 400 `"Speaker '{label}' tidak ada di transkrip"` untuk label yang tidak ada (tidak ada perubahan yang disimpan); tulis ulang `segments` sebagai list baru supaya JSONB terdeteksi berubah. **Tidak** memanggil `mark_edited`.
  - `SummaryUpdateRequest(tldr: str | None, decisions: list[str] | None, topics: list[str] | None)`. Validator: `tldr` di-strip dan 422 kalau kosong; setiap item `decisions`/`topics` di-strip, item kosong dibuang.
  - `SpeakerRenameRequest(renames: dict[str, str])`: minimal 1 entri; nama baru di-strip, 1–100 karakter (422 kalau di luar itu).
  - Route: `PATCH /api/v1/meetings/{id}/summary` → `SummaryResponse`; `PATCH /api/v1/meetings/{id}/transcript/speakers` → `TranscriptResponse`.
  - `ActionItemUpdateRequest` mendapat `task: str | None` dan `dismiss_review: bool | None` (keduanya organizer saja, 403 `"Hanya organizer yang bisa mengedit notulen"`).
  - `ActionItemResponse` mendapat `ai_assignee_text`, `ai_due_date_text`, `needs_review`.
  - `delete_action_item(db, action_item_id, user_id) -> None` + route `DELETE /api/v1/action-items/{id}` → 204; non-organizer 403.

Aturan action item: mengisi `assignee_participant_id` menghapus `ai_assignee_text`; mengisi `due_date` menghapus `ai_due_date_text`; `dismiss_review=true` menghapus keduanya. Perubahan `task`, assignee, due date, `dismiss_review`, create, dan delete oleh organizer memanggil `mark_edited`. Toggle `status` tidak.

- [ ] **Step 1: Tulis test yang gagal**
  - `test_update_summary_partial_and_strips_blank_items`: `PATCH .../summary` dengan `{"decisions": ["  Keputusan B ", "", "   "]}` → `decisions == ["Keputusan B"]`, `tldr == "Ringkasan AI"`, `meeting.notulen_edited_at is not None` (Review Focus #4).
  - `test_update_summary_rejects_blank_tldr`: `{"tldr": "   "}` → 422.
  - `test_member_cannot_edit_summary`: → 403.
  - `test_rename_speakers_updates_all_segments`: `{"renames": {"SPEAKER_00": "Budi"}}` → semua segmen ber-`speaker == "Budi"`, `notulen_edited_at is None`.
  - `test_rename_unknown_speaker_400_and_transcript_unchanged`: `{"renames": {"SPEAKER_00": "Budi", "SPEAKER_09": "Ani"}}` → 400, segmen masih `SPEAKER_00` (Review Focus #3).
  - `test_rename_blank_target_422`: `{"renames": {"SPEAKER_00": "  "}}` → 422 (Review Focus #3).
  - `test_organizer_edits_task_member_cannot`: organizer → 200, `task` berubah; member → 403.
  - `test_setting_assignee_clears_ai_assignee_text` dan `test_dismiss_review_clears_both_flags`: setelahnya `needs_review == False`.
  - `test_delete_action_item_organizer_only`: member 403; organizer 204 dan baris terhapus.
  - `test_status_toggle_does_not_mark_edited`.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_edit.py -v`
  Expected: FAIL, 404 untuk route yang belum ada.

- [ ] **Step 3: Implementasi** sesuai Interfaces.

- [ ] **Step 4: Jalankan test**
  Run: `docker compose exec backend-api pytest tests/test_notulen_edit.py -v`
  Expected: PASS (11 test).

- [ ] **Step 5: Commit**
  `git commit -m "feat(notulen): edit summary, speaker names, and action items with review flags"`

---

### Task 6: Publish, kirim ulang, email thread, label versi PDF

**Files:**
- Modify: `backend/app/services/notulen.py` (`build_published_snapshot`, `publish_notulen`, `resend_notulen`, `version_label`)
- Modify: `backend/app/routers/notulen.py` (`POST /{id}/notulen/publish`, `POST /{id}/notulen/resend` → `NotulenMeta`)
- Create: `backend/app/tasks/send_notulen.py`; Modify: `backend/app/worker.py` (tambahkan `"app.tasks.send_notulen"` ke `include`)
- Modify: `backend/app/services/email.py` (`notulen_root_message_id`, parameter baru di `send_notulen_email`)
- Modify: `backend/app/services/pdf.py` (`generate_notulen_pdf(..., version_label: str | None = None)`, dicetak di baris header tanggal)
- Modify: `backend/app/routers/meetings.py`, `backend/app/services/checkin.py` (teruskan `version_label(meeting)` ke PDF)
- Modify: `docs/API_CONTRACT.md` (tambah bagian "Review notulen" yang menautkan ke handoff FE)
- Test: `backend/tests/test_notulen_publish.py`

**Interfaces:**
- Consumes: semua yang di atas.
- Produces:
  - `build_published_snapshot(meeting: Meeting) -> dict`: bentuk `published` dari spec.
  - `publish_notulen(db, meeting_id, user_id) -> Meeting`: organizer saja; 404 `"Notulen belum tersedia"` kalau belum ada summary; 409 `"Notulen sudah dipublikasikan"` kalau status bukan `draft`. Membuat `NotulenVersion(kind=published, version=max+1, created_by=user_id)`, set status `published`, commit, lalu `send_notulen_task.delay(str(meeting.id), version)`. `IntegrityError` saat commit → rollback + 409 `"Notulen sedang dikirim, muat ulang halaman"`.
  - `resend_notulen(db, meeting_id, user_id) -> Meeting`: 409 `"Notulen belum dipublikasikan"` kalau status bukan `published`; 409 `"Tidak ada perubahan sejak versi terakhir"` kalau `has_unsent_changes` false. Selebihnya sama dengan publish.
  - `version_label(meeting: Meeting) -> str`: draft → `"DRAFT — belum dipublikasikan"`; published → `"Versi {n}"`, ditambah `" · diperbarui {dd/mm/yyyy}"` (dari `notulen_edited_at`) kalau `has_unsent_changes`.
  - `notulen_root_message_id(meeting_id: uuid.UUID, participant_id: uuid.UUID) -> str` → `"<notulen-{meeting_id}-{participant_id}@{domain}>"`, dengan `domain` = bagian setelah `@` dari `settings.SMTP_USER`, atau `"kioku.local"`.
  - `send_notulen_email(..., participant_id: uuid.UUID, version: int)`. Versi 1: `Message-ID` = root. Versi ≥ 2: `Message-ID` = `email.utils.make_msgid(domain=...)`, `In-Reply-To` = `References` = root, dan body diawali `<p><b>Versi {n}</b> — versi ini menggantikan notulen sebelumnya.</p>`. Subjek tetap `Notulen Rapat: {judul}`.
  - `send_notulen_task(meeting_id: str, version: int)`: memuat meeting beserta peserta, membuat PDF sekali dengan `version_label`, lalu memanggil `send_notulen_email` untuk setiap peserta yang punya invitation token (logika yang dipindah dari step 10 pipeline lama).

- [ ] **Step 1: Tulis test yang gagal.** Monkeypatch `app.tasks.send_notulen.send_notulen_task.delay` untuk mencatat argumen.
  - `test_publish_creates_v1_and_enqueues_email`: `POST .../notulen/publish` → 200, `body["status"] == "published"`, `body["current_version"] == 1`, `delay` dipanggil dengan `(str(meeting.id), 1)`.
  - `test_publish_twice_returns_409`.
  - `test_member_cannot_publish`: → 403.
  - `test_resend_without_changes_returns_409`: `detail == "Tidak ada perubahan sejak versi terakhir"`.
  - `test_resend_after_edit_creates_v2`: publish → `PATCH .../summary` → resend → `current_version == 2`, `has_unsent_changes == False`.
  - `test_double_resend_second_returns_409` (Review Focus #2): edit → resend 200 → resend 409; total `delay` dipanggil 2 kali (publish + satu resend).
  - `test_publish_after_redraft_continues_numbering`: sudah ada published v1, status di-set `draft` → publish → `current_version == 2`.
  - `test_version_label`: draft, published v2, dan published v2 dengan edit pada 19/11/2026 → tiga string persis dari Interfaces.
  - `test_root_message_id_domain`: `SMTP_USER = "notulen@kampus.ac.id"` → berakhiran `"@kampus.ac.id>"`; `SMTP_USER = ""` → berakhiran `"@kioku.local>"`.
  - `test_send_task_threads_followup_versions`: monkeypatch `app.services.email._smtp_connection` dengan objek palsu (context manager yang menyimpan argumen `sendmail`). Panggil `send_notulen_task(str(meeting.id), 1)` lalu `send_notulen_task(str(meeting.id), 2)`. Parse dengan `email.message_from_string`: email v1 `Message-ID == root` tanpa `In-Reply-To`; email v2 `In-Reply-To == root`, `References == root`, `Subject == "Notulen Rapat: Team Sync"`.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_notulen_publish.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implementasi** sesuai Interfaces.

- [ ] **Step 4: Jalankan test**
  Run: `docker compose exec backend-api pytest tests/test_notulen_publish.py -v`
  Expected: PASS (10 test).

- [ ] **Step 5: Verifikasi manual threading.** Restart `backend-api` dan `celery-worker`. Publish satu meeting, edit, lalu kirim ulang.
  Expected: di Mailhog ada dua email dengan header `In-Reply-To` yang benar. Kalau memakai Gmail sungguhan (setup expo), kedua email muncul sebagai **satu thread** di inbox penerima. Kalau tidak menyatu, catat sebagai risiko di spec; jangan ubah format Message-ID tanpa diskusi.

- [ ] **Step 6: Commit**
  `git commit -m "feat(notulen): publish and resend notulen as threaded, versioned email"`

---

### Task 7: Hapus audio tidak menghapus notulen, ganti rekaman mengosongkan status

**Files:**
- Modify: `backend/app/services/recording.py`
- Modify: `docs/API_CONTRACT.md` (deskripsi `DELETE /meetings/{id}/recording`)
- Test: `backend/tests/test_recording_notulen.py`

**Interfaces:**
- Produces:
  - `delete_recording(...)` hanya memanggil `storage.delete_file` dan menghapus baris `Recording`. Transkrip, ringkasan, action item, dan status notulen tidak disentuh.
  - `_delete_recording_records` diganti nama menjadi `_clear_previous_processing(db: Session, recording: Recording, meeting: Meeting) -> None`. Hanya dipakai di jalur upload pengganti. Perilakunya: hapus transkrip, summary, dan action item `source=ai` seperti sebelumnya, lalu set `meeting.notulen_status = None` dan `meeting.notulen_edited_at = None`. Baris `notulen_versions` **tidak** dihapus.

- [ ] **Step 1: Tulis test yang gagal**
  - `test_delete_recording_keeps_published_notulen`: monkeypatch `app.services.storage.delete_file`; `DELETE /api/v1/meetings/{id}/recording` sebagai organizer → 204; `Summary` masih ada, `notulen_status == published`, `Recording` sudah tidak ada.
  - `test_clear_previous_processing_resets_status_keeps_versions`: meeting published dengan satu `NotulenVersion` v1 → panggil `_clear_previous_processing` dan commit → `notulen_status is None`, `Summary` hilang, `NotulenVersion` v1 masih ada.

- [ ] **Step 2: Jalankan, pastikan gagal**
  Run: `docker compose exec backend-api pytest tests/test_recording_notulen.py -v`
  Expected: FAIL, summary ikut terhapus.

- [ ] **Step 3: Implementasi** sesuai Interfaces.

- [ ] **Step 4: Jalankan seluruh suite**
  Run: `make test`
  Expected: PASS semua, termasuk test lama.

- [ ] **Step 5: Commit**
  `git commit -m "feat(notulen): keep notulen when audio is deleted, reset status on replacement"`

---

## Setelah semua task selesai

1. Buka PR `feature/backend-notulen-review` → `main`.
2. Kirim [`notulen-review-frontend-handoff.md`](./notulen-review-frontend-handoff.md) ke Helena, beserta nama branch atau link PR-nya. Isinya adalah kontrak API yang baru saja dibuat.
3. Kalau ada pesan error atau bentuk respons yang berubah selama implementasi, **perbarui handoff sebelum dikirim**.
