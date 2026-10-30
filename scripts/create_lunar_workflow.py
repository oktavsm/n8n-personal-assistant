#!/usr/bin/env python3
"""Generator for lunar-hub-api n8n workflow.

Exposes a clean webhook for Lunar Hub desktop client:
POST https://oktaavsm.bccdev.id/n8n/webhook/lunar-agenda
1. Query today's agenda, GCal kuliah, personal agenda, tugas, and Brone LMS tasks.
2. Create new calendar events directly from Lunar Hub quick capture.
3. Zero Emoji Rule strictly enforced across all responses.
"""

import json
from pathlib import Path

WORKFLOW_ID = "lunarHubApi2026"
WORKFLOW_NAME = "lunar-hub-api"
WEBHOOK_ID = "f0a1b2c3-4d5e-6f70-8192-a3b4c5d6e7f8"

aggregate_code = """
const cleanText = (text) => {
  if (!text) return "";
  return String(text)
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\\s+/g, " ")
    .trim();
};

const parseTitle = (summary) => {
  const text = cleanText(summary);
  if (!text) {
    return {
      title: "Tanpa Judul",
      task_name: "",
      course: "",
      code: "",
      course_name: "",
      room: "",
      cleanTitle: "",
      is_task: false
    };
  }

  // Pattern 1: [Tugas] Course Name (CODE) - Task Detail
  // E.g. [Tugas] Pengembangan Aplikasi Perangkat Bergerak (PAPB) - Laporan Praktikum
  const mTaskWithCode = text.match(/^\\[(.*?)\\]\\s*(.*?)\\s*\\((.*?)\\)\\s*[-–]\\s*(.*)$/);
  if (mTaskWithCode) {
    const tag = cleanText(mTaskWithCode[1]);
    const courseName = cleanText(mTaskWithCode[2]);
    const courseCode = cleanText(mTaskWithCode[3]);
    const taskDetail = cleanText(mTaskWithCode[4]);
    return {
      title: taskDetail,
      task_name: taskDetail,
      course: courseCode || courseName,
      code: courseCode,
      course_name: courseName,
      room: "",
      cleanTitle: text,
      is_task: true
    };
  }

  // Pattern 2: [Tugas] Course Name - Task Detail (no parentheses code)
  const mTaskNoCode = text.match(/^\\[(.*?)\\]\\s*(.*?)\\s*[-–]\\s*(.*)$/);
  if (mTaskNoCode) {
    const tag = cleanText(mTaskNoCode[1]);
    const courseName = cleanText(mTaskNoCode[2]);
    const taskDetail = cleanText(mTaskNoCode[3]);
    return {
      title: taskDetail,
      task_name: taskDetail,
      course: courseName,
      code: "",
      course_name: courseName,
      room: "",
      cleanTitle: text,
      is_task: tag.toLowerCase().includes("tugas")
    };
  }

  // Pattern 3: Tugas: Task Name (from Google Classroom)
  // E.g. Tugas: UTP Pengembangan Aplikasi Perangkat Bergerak
  const mClassroomTask = text.match(/^Tugas:\\s*(.*)$/i);
  if (mClassroomTask) {
    const taskDetail = cleanText(mClassroomTask[1]);
    return {
      title: taskDetail,
      task_name: taskDetail,
      course: "PAPB",
      code: "PAPB",
      course_name: "Pengembangan Aplikasi Perangkat Bergerak",
      room: "",
      cleanTitle: text,
      is_task: true
    };
  }

  // Pattern 4: Room - Course Name (e.g. G1.4 - Praktikum PAPB, F3.1 - Jaringan Nirkabel)
  const mRoom = text.match(/^([A-Za-z][0-9]\\.[0-9]+[A-Za-z0-9]*)\\s*[-–]\\s*(.*)$/);
  if (mRoom) {
    const room = cleanText(mRoom[1]);
    const course = cleanText(mRoom[2]);
    return {
      title: text,
      task_name: "",
      course: course,
      code: "",
      course_name: course,
      room: room,
      cleanTitle: text,
      is_task: false
    };
  }

  // Pattern 5: [TAG] Something (e.g. [ASPRAK] Menginfokan Materi...)
  const mTagOnly = text.match(/^\\[(.*?)\\]\\s*(.*)$/);
  if (mTagOnly) {
    const tag = cleanText(mTagOnly[1]);
    const subject = cleanText(mTagOnly[2]);
    return {
      title: text,
      task_name: "",
      course: subject,
      code: tag,
      course_name: subject,
      room: "",
      cleanTitle: text,
      is_task: tag.toLowerCase().includes("tugas")
    };
  }

  return {
    title: text,
    task_name: "",
    course: text,
    code: "",
    course_name: text,
    room: "",
    cleanTitle: text,
    is_task: false
  };
};

const parseDescription = (desc) => {
  const text = cleanText(desc);
  const result = { prodi: "", kelas: "", ruang: "", dosen: "" };
  const labels = ["Prodi", "Kelas", "Ruang", "Dosen"];
  labels.forEach((label, idx) => {
    const nextLabels = labels.slice(idx + 1).join("|");
    const regex = nextLabels
      ? new RegExp(`${label}:\\\\s*(.*?)(?=,\\\\s*(?:${nextLabels}):|$)`, "i")
      : new RegExp(`${label}:\\\\s*(.*)$`, "i");
    const m = text.match(regex);
    if (m) {
      result[label.toLowerCase()] = cleanText(m[1]).replace(/,$/, "");
    }
  });
  return result;
};

const now = new Date();

const formatTimeRange = (startDt, endDt, isAllDay) => {
  if (isAllDay || !startDt) return "Seharian";
  const startStr = startDt.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" });
  if (!endDt) return startStr;
  const endStr = endDt.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" });
  return `${startStr} - ${endStr}`;
};

const formatDateWIB = (dt) => {
  return dt.toLocaleDateString("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Jakarta"
  });
};

const isToday = (dt) => {
  const dtStr = dt.toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });
  const nowStr = now.toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });
  return dtStr === nowStr;
};

const isTomorrow = (dt) => {
  const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
  const dtStr = dt.toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });
  const tomStr = tomorrow.toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });
  return dtStr === tomStr;
};

// Retrieve collected items safely
const safeGetItems = (nodeName) => {
  try {
    const nodeObj = $(nodeName).first();
    const items = nodeObj?.json?.items;
    if (Array.isArray(items)) {
      return items.filter(it => it && (it.id || it.summary || it.name));
    }
    return [];
  } catch (e) {
    return [];
  }
};

const kuliahItems = safeGetItems("Collect Kuliah");
const agendaItems = safeGetItems("Collect Agenda");
const tugasItems = safeGetItems("Collect Tugas");
const papbItems = safeGetItems("Collect PAPB");

const allRawEvents = [];

const processGCalItem = (j, defaultCategory, sourceName) => {
  if (!j) return;
  if (!j.summary && !j.name && !j.id) return;

  const isAllDay = !j.start?.dateTime && !!j.start?.date;
  const startDt = j.start?.dateTime ? new Date(j.start.dateTime) : (j.start?.date ? new Date(`${j.start.date}T00:00:00+07:00`) : null);
  const endDt = j.end?.dateTime ? new Date(j.end.dateTime) : (j.end?.date ? new Date(`${j.end.date}T23:59:59+07:00`) : null);

  if (!startDt) return;

  const rawSummary = cleanText(j.summary || j.name || "(Kegiatan Tanpa Judul)");
  const titleInfo = parseTitle(rawSummary);
  const descInfo = parseDescription(j.description || "");

  const location = cleanText(j.location || titleInfo.room || descInfo.ruang || "");
  const isTaskCategory = titleInfo.is_task || defaultCategory === "Tugas";
  const category = isTaskCategory ? "Tugas" : defaultCategory;

  const eventTitle = isTaskCategory
    ? (titleInfo.task_name || titleInfo.title || rawSummary)
    : (titleInfo.title || titleInfo.course || rawSummary);

  const diffMs = startDt.getTime() - now.getTime();
  const minutesUntil = Math.round(diffMs / 60000);
  const isNow = now >= startDt && endDt && now <= endDt;
  const isDone = endDt ? now > endDt : now > startDt;

  let timeStatus = "";
  if (isNow) timeStatus = "NOW";
  else if (isDone) timeStatus = "DONE";
  else if (minutesUntil > 0 && minutesUntil <= 60) timeStatus = `${minutesUntil}m lagi`;
  else if (minutesUntil > 60 && minutesUntil <= 1440) timeStatus = `${Math.round(minutesUntil / 60)}h lagi`;
  else if (minutesUntil > 1440) timeStatus = `${Math.round(minutesUntil / 1440)}d lagi`;

  allRawEvents.push({
    id: j.id || `gcal-${Math.random()}`,
    title: eventTitle,
    raw_title: rawSummary,
    course: titleInfo.course || (category === "Kuliah" ? "Kuliah" : "Agenda"),
    code: titleInfo.code || "",
    course_name: titleInfo.course_name || titleInfo.course || "",
    task_name: titleInfo.task_name || "",
    type: titleInfo.code || titleInfo.type || "",
    category: category,
    source: sourceName,
    start_time: startDt.toISOString(),
    end_time: endDt ? endDt.toISOString() : startDt.toISOString(),
    time_formatted: formatTimeRange(startDt, endDt, isAllDay),
    date_formatted: formatDateWIB(startDt),
    location: location,
    kelas: descInfo.kelas,
    dosen: descInfo.dosen,
    is_today: isToday(startDt),
    is_tomorrow: isTomorrow(startDt),
    is_now: isNow,
    is_done: isDone,
    time_status: timeStatus,
    minutes_until: minutesUntil,
    all_day: isAllDay
  });
};

kuliahItems.forEach(it => processGCalItem(it, "Kuliah", "gcal_kuliah"));
agendaItems.forEach(it => processGCalItem(it, "Agenda", "gcal_agenda"));
tugasItems.forEach(it => processGCalItem(it, "Tugas", "gcal_tugas"));
papbItems.forEach(it => processGCalItem(it, "Kuliah", "gcal_papb"));

// De-duplicate by raw_title + start_time
const seenKeys = new Set();
const uniqueEvents = [];
for (const ev of allRawEvents) {
  const key = `${ev.raw_title}|${ev.start_time}`;
  if (!seenKeys.has(key)) {
    seenKeys.add(key);
    uniqueEvents.push(ev);
  }
}

// Sort chronologically
uniqueEvents.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

const todayEvents = uniqueEvents.filter(e => e.is_today && e.category !== "Tugas");
const tomorrowEvents = uniqueEvents.filter(e => e.is_tomorrow && e.category !== "Tugas");
const upcomingEvents = uniqueEvents.filter(e => !e.is_today && e.category !== "Tugas");

// Process Brone LMS Tasks
const academicTasks = [];
try {
  const broneResp = $("HTTP Brone Get Tasks").first()?.json;
  let rawEvents = [];
  if (Array.isArray(broneResp) && broneResp[0] && broneResp[0].data && Array.isArray(broneResp[0].data.events)) {
    rawEvents = broneResp[0].data.events;
  }

  for (const b of rawEvents) {
    const timestamp = b.timesort || b.timestart;
    const deadlineDt = timestamp ? new Date(timestamp * 1000) : null;
    const hoursLeft = deadlineDt ? Math.round((deadlineDt.getTime() - now.getTime()) / 3600000) : null;
    const courseFullName = cleanText(b.course?.fullname || b.course?.shortname || "Kuliah UB");

    let courseCode = cleanText(b.course?.shortname || "");
    const mCode = courseFullName.match(/\\((.*?)\\)/);
    if (!courseCode && mCode) courseCode = mCode[1];

    academicTasks.push({
      id: `brone-${b.id || Math.random()}`,
      title: cleanText(b.name || "Tugas Tanpa Judul"),
      course: courseCode || courseFullName,
      code: courseCode,
      course_name: courseFullName,
      raw_title: cleanText(b.name || "Tugas Tanpa Judul"),
      category: "Academic",
      source: "brone_lms",
      deadline: deadlineDt ? deadlineDt.toISOString() : null,
      deadline_formatted: deadlineDt ? formatDateWIB(deadlineDt) : "-",
      time_formatted: deadlineDt ? deadlineDt.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }) : "-",
      hours_left: hoursLeft,
      is_due_soon: hoursLeft !== null && hoursLeft >= 0 && hoursLeft <= 48,
      url: b.url || b.action?.url || ""
    });
  }
} catch (e) {
  // Graceful fallback
}

// Also add GCal Tugas to academicTasks if not present
for (const t of uniqueEvents.filter(e => e.category === "Tugas")) {
  const deadlineDt = new Date(t.start_time);
  const hoursLeft = Math.round((deadlineDt.getTime() - now.getTime()) / 3600000);
  academicTasks.push({
    id: t.id,
    title: t.task_name || t.title,
    course: t.code || t.course || "Tugas",
    code: t.code || "",
    course_name: t.course_name || t.course || "",
    raw_title: t.raw_title,
    category: "Academic",
    source: t.source || "gcal_tugas",
    deadline: t.start_time,
    deadline_formatted: t.date_formatted,
    time_formatted: t.time_formatted,
    hours_left: hoursLeft,
    is_due_soon: hoursLeft >= 0 && hoursLeft <= 48,
    url: ""
  });
}

// Sort tasks by deadline
academicTasks.sort((a, b) => {
  if (!a.deadline) return 1;
  if (!b.deadline) return -1;
  return new Date(a.deadline) - new Date(b.deadline);
});

// Process SIAM Announcements
const announcements = [];
try {
  const siamResp = $("HTTP SIAM Announcements").first()?.json;
  let rawAnnouncements = [];
  if (siamResp && Array.isArray(siamResp.data)) {
    rawAnnouncements = siamResp.data;
  }

  const todayStr = now.toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });

  for (const m of rawAnnouncements) {
    const courseName = cleanText(m.matkul || "Mata Kuliah");
    const courseCode = cleanText(m.kode || "");
    const courseKelas = cleanText(m.kelas || "");

    for (const p of (m.daftar_pengumuman || [])) {
      const content = cleanText(p.isi || "");
      if (!content) continue;

      const dateStr = cleanText(p.tanggal || "");
      let dateFormatted = dateStr;
      if (dateStr) {
        try {
          const d = new Date(`${dateStr}T00:00:00+07:00`);
          dateFormatted = formatDateWIB(d);
        } catch (e) {}
      }

      const isTodayAnnounce = dateStr === todayStr;

      let hash = 0;
      const keyStr = `${courseCode}_${courseKelas}_${dateStr}_${content.slice(0, 40)}`;
      for (let i = 0; i < keyStr.length; i++) {
        hash = ((hash << 5) - hash) + keyStr.charCodeAt(i);
        hash |= 0;
      }
      const itemKey = `siam-${Math.abs(hash)}`;

      announcements.push({
        id: itemKey,
        course: courseName,
        code: courseCode,
        kelas: courseKelas,
        date: dateStr,
        date_formatted: dateFormatted,
        content: content,
        is_today: isTodayAnnounce
      });
    }
  }
} catch (e) {
  // Graceful fallback
}

// Sort announcements newest date first
announcements.sort((a, b) => (b.date || "").localeCompare(a.date || ""));

return [{
  json: {
    status: "success",
    synced_at: now.toISOString(),
    today_events: todayEvents,
    tomorrow_events: tomorrowEvents,
    upcoming_events: upcomingEvents.slice(0, 10),
    academic_tasks: academicTasks,
    announcements: announcements,
    stats: {
      today_events_count: todayEvents.length,
      upcoming_count: upcomingEvents.length,
      tasks_count: academicTasks.length,
      due_soon_count: academicTasks.filter(t => t.is_due_soon).length,
      announcements_count: announcements.length,
      today_announcements_count: announcements.filter(a => a.is_today).length
    }
  }
}];
"""

workflow = {
    "id": WORKFLOW_ID,
    "name": WORKFLOW_NAME,
    "active": True,
    "nodes": [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "lunar-agenda",
                "responseMode": "responseNode",
                "options": {}
            },
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2.1,
            "position": [-300, 200],
            "id": "node-webhook-lunar",
            "name": "Webhook",
            "webhookId": WEBHOOK_ID
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2
                    },
                    "conditions": [
                        {
                            "leftValue": "={{ $json.body?.action }}",
                            "rightValue": "create_event",
                            "operator": {
                                "type": "string",
                                "operation": "equals"
                            }
                        }
                    ],
                    "combinator": "and"
                }
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [-50, 200],
            "id": "node-if-create-event",
            "name": "If: Is Create Event"
        },
        {
            "parameters": {
                "calendar": {
                    "__rl": True,
                    "value": "={{ $json.body.calendar || ($json.body.category === 'Kuliah' ? $env.GCAL_OKTA_KULIAH : ($json.body.category === 'Tugas' ? $env.GCAL_OKTA_TUGAS : $env.GCAL_OKTA_AGENDA)) }}",
                    "mode": "id"
                },
                "start": "={{ $json.body.start }}",
                "end": "={{ $json.body.end }}",
                "additionalFields": {
                    "summary": "={{ $json.body.summary || $json.body.title }}",
                    "description": "={{ $json.body.description || '' }}",
                    "location": "={{ $json.body.location || '' }}"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [250, 50],
            "id": "node-create-gcal-event",
            "name": "Create GCal Event",
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { status: 'success', action: 'created', event: $json, id: $json.id, summary: $json.summary || $('Webhook').first().json.body.summary, start: $json.start?.dateTime || $('Webhook').first().json.body.start, end: $json.end?.dateTime || $('Webhook').first().json.body.end, location: $json.location || $('Webhook').first().json.body.location || '', category: $('Webhook').first().json.body.category || 'Agenda' } }}",
                "options": {
                    "responseCode": 201,
                    "responseHeaders": {
                        "entries": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Access-Control-Allow-Origin", "value": "*"}
                        ]
                    }
                }
            },
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.5,
            "position": [500, 50],
            "id": "node-respond-created",
            "name": "Respond: Event Created"
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2
                    },
                    "conditions": [
                        {
                            "leftValue": "={{ $json.body?.action }}",
                            "rightValue": "delete_event",
                            "operator": {
                                "type": "string",
                                "operation": "equals"
                            }
                        }
                    ],
                    "combinator": "and"
                }
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [-50, 350],
            "id": "node-if-delete-event",
            "name": "If: Is Delete Event"
        },
        {
            "parameters": {
                "operation": "delete",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $json.body.calendar || ($json.body.category === 'Kuliah' ? $env.GCAL_OKTA_KULIAH : ($json.body.category === 'Tugas' ? $env.GCAL_OKTA_TUGAS : $env.GCAL_OKTA_AGENDA)) }}",
                    "mode": "id"
                },
                "eventId": "={{ $json.body.eventId || $json.body.id }}",
                "options": {}
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [250, 200],
            "id": "node-delete-gcal-event",
            "name": "Delete GCal Event",
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { status: 'success', action: 'deleted', id: $('Webhook').first().json.body.eventId || $('Webhook').first().json.body.id } }}",
                "options": {
                    "responseCode": 200,
                    "responseHeaders": {
                        "entries": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Access-Control-Allow-Origin", "value": "*"}
                        ]
                    }
                }
            },
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.5,
            "position": [500, 200],
            "id": "node-respond-deleted",
            "name": "Respond: Event Deleted"
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_OKTA_KULIAH }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.startOf('day').toISO() }}",
                "timeMax": "={{ $now.plus({ days: 4 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True,
                    "orderBy": "startTime"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [200, 350],
            "id": "node-get-gcal-kuliah",
            "name": "Get GCal Kuliah",
            "alwaysOutputData": True,
            "continueOnFail": True,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "jsCode": "return [{ json: { items: $input.all().map(i => i.json).filter(Boolean) } }];"
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [400, 350],
            "id": "node-collect-kuliah",
            "name": "Collect Kuliah"
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_OKTA_AGENDA }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.startOf('day').toISO() }}",
                "timeMax": "={{ $now.plus({ days: 4 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True,
                    "orderBy": "startTime"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [600, 350],
            "id": "node-get-gcal-agenda",
            "name": "Get GCal Agenda",
            "alwaysOutputData": True,
            "continueOnFail": True,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "jsCode": "return [{ json: { items: $input.all().map(i => i.json).filter(Boolean) } }];"
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [800, 350],
            "id": "node-collect-agenda",
            "name": "Collect Agenda"
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_OKTA_TUGAS }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.startOf('day').toISO() }}",
                "timeMax": "={{ $now.plus({ days: 14 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True,
                    "orderBy": "startTime"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [1000, 350],
            "id": "node-get-gcal-tugas",
            "name": "Get GCal Tugas",
            "alwaysOutputData": True,
            "continueOnFail": True,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "jsCode": "return [{ json: { items: $input.all().map(i => i.json).filter(Boolean) } }];"
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1200, 350],
            "id": "node-collect-tugas",
            "name": "Collect Tugas"
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_CLASS_PAPB }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.startOf('day').toISO() }}",
                "timeMax": "={{ $now.plus({ days: 4 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True,
                    "orderBy": "startTime"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [1400, 350],
            "id": "node-get-gcal-papb",
            "name": "Get GCal PAPB",
            "alwaysOutputData": True,
            "continueOnFail": True,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "jsCode": "return [{ json: { items: $input.all().map(i => i.json).filter(Boolean) } }];"
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1600, 350],
            "id": "node-collect-papb",
            "name": "Collect PAPB"
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://brone-auth:3000/get-cookies",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={\n  \"username\": \"{{ $env.BRONE_USERNAME }}\",\n  \"password\": \"{{ $env.BRONE_PASSWORD }}\"\n}",
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.4,
            "position": [1800, 350],
            "id": "node-brone-auth",
            "name": "HTTP Brone Auth",
            "alwaysOutputData": True,
            "continueOnFail": True
        },
        {
            "parameters": {
                "method": "POST",
                "url": "=https://brone.ub.ac.id/lib/ajax/service.php?sesskey={{ $json.sesskey }}&info=core_calendar_get_action_events_by_timesort",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Cookie",
                            "value": "={{ $json.cookieString }}"
                        }
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "=[\n    {\n        \"index\": 0,\n        \"methodname\": \"core_calendar_get_action_events_by_timesort\",\n        \"args\": {\n            \"limitnum\": 10,\n            \"timesortfrom\": {{ Math.floor(Date.now() / 1000) }},\n            \"limittononsuspendedevents\": true\n        }\n    }\n]",
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.4,
            "position": [2000, 350],
            "id": "node-brone-tasks",
            "name": "HTTP Brone Get Tasks",
            "alwaysOutputData": True,
            "continueOnFail": True
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://brone-auth:3000/get-siam-pengumuman",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={\n  \"username\": \"{{ $env.BRONE_USERNAME }}\",\n  \"password\": \"{{ $env.BRONE_PASSWORD }}\"\n}",
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.4,
            "position": [2200, 350],
            "id": "node-siam-announcements",
            "name": "HTTP SIAM Announcements",
            "alwaysOutputData": True,
            "continueOnFail": True
        },
        {
            "parameters": {
                "jsCode": aggregate_code.strip()
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2400, 350],
            "id": "node-aggregate-agenda",
            "name": "Aggregate & Format Agenda"
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {
                    "responseCode": 200,
                    "responseHeaders": {
                        "entries": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Access-Control-Allow-Origin", "value": "*"}
                        ]
                    }
                }
            },
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.5,
            "position": [2600, 350],
            "id": "node-respond-agenda",
            "name": "Respond: Agenda Data"
        }
    ],
    "connections": {
        "Webhook": {
            "main": [
                [
                    {
                        "node": "If: Is Create Event",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "If: Is Create Event": {
            "main": [
                [
                    {
                        "node": "Create GCal Event",
                        "type": "main",
                        "index": 0
                    }
                ],
                [
                    {
                        "node": "If: Is Delete Event",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Create GCal Event": {
            "main": [
                [
                    {
                        "node": "Respond: Event Created",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "If: Is Delete Event": {
            "main": [
                [
                    {
                        "node": "Delete GCal Event",
                        "type": "main",
                        "index": 0
                    }
                ],
                [
                    {
                        "node": "Get GCal Kuliah",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Delete GCal Event": {
            "main": [
                [
                    {
                        "node": "Respond: Event Deleted",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Get GCal Kuliah": {
            "main": [
                [
                    {
                        "node": "Collect Kuliah",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Collect Kuliah": {
            "main": [
                [
                    {
                        "node": "Get GCal Agenda",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Get GCal Agenda": {
            "main": [
                [
                    {
                        "node": "Collect Agenda",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Collect Agenda": {
            "main": [
                [
                    {
                        "node": "Get GCal Tugas",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Get GCal Tugas": {
            "main": [
                [
                    {
                        "node": "Collect Tugas",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Collect Tugas": {
            "main": [
                [
                    {
                        "node": "Get GCal PAPB",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Get GCal PAPB": {
            "main": [
                [
                    {
                        "node": "Collect PAPB",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Collect PAPB": {
            "main": [
                [
                    {
                        "node": "HTTP Brone Auth",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "HTTP Brone Auth": {
            "main": [
                [
                    {
                        "node": "HTTP Brone Get Tasks",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "HTTP Brone Get Tasks": {
            "main": [
                [
                    {
                        "node": "HTTP SIAM Announcements",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "HTTP SIAM Announcements": {
            "main": [
                [
                    {
                        "node": "Aggregate & Format Agenda",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Aggregate & Format Agenda": {
            "main": [
                [
                    {
                        "node": "Respond: Agenda Data",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    },
    "settings": {
        "executionOrder": "v1"
    }
}

target_paths = [
    Path("/home/oktaavsm/Code/github.com/n8n-personal-assistant/workflow/lunar-hub-api.json"),
    Path("/home/oktaavsm/Code/github.com/n8n-personal-assistant/n8n/workflow/lunar-hub-api.json")
]

for p in target_paths:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump([workflow], f, indent=2)
    print(f"Generated: {p}")
