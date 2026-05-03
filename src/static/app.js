const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const uploadForm = document.getElementById("uploadForm");
const actionInput = document.getElementById("actionInput");
const actionButtons = document.querySelectorAll(".action-button");

const resultSection = document.getElementById("resultSection");
const statusStep = document.getElementById("statusStep");
const statusMessage = document.getElementById("statusMessage");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const transcriptTitle = document.getElementById("transcriptTitle");
const transcriptBox = document.getElementById("transcriptBox");
const downloadTitle = document.getElementById("downloadTitle");
const downloadList = document.getElementById("downloadList");
const resetLink = document.getElementById("resetLink");

let pollingTimer = null;
let lastTranscript = "";

function updateFileName(file) {
    if (file) {
        fileName.textContent = `선택된 파일: ${file.name}`;
    } else {
        fileName.textContent = "선택된 파일 없음";
    }
}

function setButtonsDisabled(disabled) {
    actionButtons.forEach((button) => {
        button.disabled = disabled;
    });
}

function resetButtonLabels() {
    actionButtons[0].textContent = "MP3만 만들기";
    actionButtons[1].textContent = "받아쓰기만 하기";
    actionButtons[2].textContent = "MP3 + 받아쓰기";
}

function showStatus(step, message, progress) {
    resultSection.style.display = "block";
    statusStep.textContent = step || "진행 중";
    statusMessage.textContent = message || "";

    const numericProgress = Number(progress || 0);
    const safeProgress = Math.max(0, Math.min(100, numericProgress));

    progressBar.style.width = `${safeProgress}%`;
    progressText.textContent = `${safeProgress}%`;
}

function showTranscript(text) {
    if (!text) {
        return;
    }

    transcriptTitle.style.display = "block";
    transcriptBox.style.display = "block";

    if (text !== lastTranscript) {
        transcriptBox.textContent = text;
        transcriptBox.scrollTop = transcriptBox.scrollHeight;
        lastTranscript = text;
    }
}

function showDownloads(job) {
    downloadList.innerHTML = "";

    if (job.mp3_url) {
        const mp3Item = document.createElement("li");
        const mp3Link = document.createElement("a");

        mp3Link.href = job.mp3_url;
        mp3Link.textContent = "MP3 다운로드";

        mp3Item.appendChild(mp3Link);
        downloadList.appendChild(mp3Item);
    }

    if (job.txt_url) {
        const txtItem = document.createElement("li");
        const txtLink = document.createElement("a");

        txtLink.href = job.txt_url;
        txtLink.textContent = "TXT 다운로드";

        txtItem.appendChild(txtLink);
        downloadList.appendChild(txtItem);
    }

    if (job.mp3_url || job.txt_url) {
        downloadTitle.style.display = "block";
    }

    if (job.cleanup_url) {
        resetLink.href = job.cleanup_url;
        resetLink.style.display = "inline-block";
    }
}

async function pollJob(jobId) {
    try {
        const response = await fetch(`/jobs/${jobId}`, {
            cache: "no-store",
        });

        const job = await response.json();

        showStatus(job.step, job.message, job.progress);
        showTranscript(job.transcript);
        showDownloads(job);

        if (job.status === "complete" || job.status === "failed") {
            if (pollingTimer) {
                clearInterval(pollingTimer);
                pollingTimer = null;
            }

            setButtonsDisabled(false);
            resetButtonLabels();

            if (job.status === "failed") {
                showStatus(
                    "오류 발생",
                    job.message || "작업 중 오류가 발생했습니다.",
                    100
                );
            }
        }
    } catch (error) {
        if (pollingTimer) {
            clearInterval(pollingTimer);
            pollingTimer = null;
        }

        setButtonsDisabled(false);
        resetButtonLabels();
        showStatus("오류 발생", "작업 상태를 가져오지 못했습니다.", 100);
    }
}

function resetResultArea() {
    lastTranscript = "";

    resultSection.style.display = "none";

    statusStep.textContent = "대기 중";
    statusMessage.textContent = "작업을 기다리고 있습니다.";
    progressBar.style.width = "0%";
    progressText.textContent = "0%";

    transcriptTitle.style.display = "none";
    transcriptBox.style.display = "none";
    transcriptBox.textContent = "";

    downloadTitle.style.display = "none";
    downloadList.innerHTML = "";

    resetLink.style.display = "none";
    resetLink.href = "/";
}

async function startJob(action, clickedButton) {
    if (!fileInput.files.length) {
        alert("먼저 파일을 선택해주세요.");
        return;
    }

    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }

    actionInput.value = action;

    const formData = new FormData(uploadForm);
    formData.set("action", action);

    resetResultArea();

    setButtonsDisabled(true);
    clickedButton.textContent = "처리 중입니다...";

    showStatus("업로드 중", "파일을 서버로 업로드하고 있습니다.", 5);

    try {
        const response = await fetch("/jobs", {
            method: "POST",
            body: formData,
            cache: "no-store",
        });

        const data = await response.json();

        if (!response.ok) {
            setButtonsDisabled(false);
            resetButtonLabels();
            showStatus("오류 발생", "작업을 시작하지 못했습니다.", 100);
            return;
        }

        pollingTimer = setInterval(() => {
            pollJob(data.job_id);
        }, 500);

        pollJob(data.job_id);
    } catch (error) {
        setButtonsDisabled(false);
        resetButtonLabels();
        showStatus("오류 발생", "서버 요청 중 오류가 발생했습니다.", 100);
    }
}

fileInput.addEventListener("change", () => {
    updateFileName(fileInput.files[0]);
});

uploadBox.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadBox.classList.add("drag-over");
});

uploadBox.addEventListener("dragleave", () => {
    uploadBox.classList.remove("drag-over");
});

uploadBox.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadBox.classList.remove("drag-over");

    const droppedFile = event.dataTransfer.files[0];

    if (!droppedFile) {
        return;
    }

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(droppedFile);
    fileInput.files = dataTransfer.files;

    updateFileName(droppedFile);
});

actionButtons.forEach((button) => {
    button.addEventListener("click", () => {
        startJob(button.dataset.action, button);
    });
});

function setupNavigationMenu() {
    const menuButton = document.getElementById("menuButton");
    const closeMenuButton = document.getElementById("closeMenuButton");
    const sideMenu = document.getElementById("sideMenu");
    const menuOverlay = document.getElementById("menuOverlay");

    if (!menuButton || !closeMenuButton || !sideMenu || !menuOverlay) {
        return;
    }

    function openMenu() {
        sideMenu.classList.add("open");
        menuOverlay.classList.add("open");
    }

    function closeMenu() {
        sideMenu.classList.remove("open");
        menuOverlay.classList.remove("open");
    }

    function toggleMenu() {
        if (sideMenu.classList.contains("open")) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    menuButton.addEventListener("click", toggleMenu);
    closeMenuButton.addEventListener("click", closeMenu);
    menuOverlay.addEventListener("click", closeMenu);
}

setupNavigationMenu();