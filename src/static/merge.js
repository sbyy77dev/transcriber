const mergeUploadBox = document.getElementById("mergeUploadBox");
const mergeFileInput = document.getElementById("mergeFileInput");
const mergeFileCount = document.getElementById("mergeFileCount");
const fileListSection = document.getElementById("fileListSection");
const mergeFileList = document.getElementById("mergeFileList");
const mergeButton = document.getElementById("mergeButton");

const mergeResultSection = document.getElementById("mergeResultSection");
const mergeStatusStep = document.getElementById("mergeStatusStep");
const mergeStatusMessage = document.getElementById("mergeStatusMessage");
const mergeProgressBar = document.getElementById("mergeProgressBar");
const mergeProgressText = document.getElementById("mergeProgressText");
const mergeDownloadTitle = document.getElementById("mergeDownloadTitle");
const mergeDownloadList = document.getElementById("mergeDownloadList");
const mergeResetLink = document.getElementById("mergeResetLink");

let selectedFiles = [];
let mergePollingTimer = null;

function updateMergeFileCount() {
    if (selectedFiles.length === 0) {
        mergeFileCount.textContent = "선택된 파일 없음";
        fileListSection.style.display = "none";
        return;
    }

    mergeFileCount.textContent = `선택된 파일 ${selectedFiles.length}개`;
    fileListSection.style.display = "block";
}

function renderMergeFileList() {
    mergeFileList.innerHTML = "";

    selectedFiles.forEach((file, index) => {
        const item = document.createElement("li");
        item.className = "merge-file-item";

        const order = document.createElement("div");
        order.className = "merge-file-order";
        order.textContent = `${index + 1}`;

        const name = document.createElement("div");
        name.className = "merge-file-name";
        name.textContent = file.name;
        name.title = file.name;

        const upButton = document.createElement("button");
        upButton.className = "order-button";
        upButton.type = "button";
        upButton.textContent = "위로";
        upButton.disabled = index === 0;
        upButton.addEventListener("click", () => {
            moveFile(index, index - 1);
        });

        const downButton = document.createElement("button");
        downButton.className = "order-button";
        downButton.type = "button";
        downButton.textContent = "아래로";
        downButton.disabled = index === selectedFiles.length - 1;
        downButton.addEventListener("click", () => {
            moveFile(index, index + 1);
        });

        item.appendChild(order);
        item.appendChild(name);
        item.appendChild(upButton);
        item.appendChild(downButton);

        mergeFileList.appendChild(item);
    });

    updateMergeFileCount();
}

function moveFile(fromIndex, toIndex) {
    if (
        toIndex < 0 ||
        toIndex >= selectedFiles.length ||
        fromIndex === toIndex
    ) {
        return;
    }

    const [movedFile] = selectedFiles.splice(fromIndex, 1);
    selectedFiles.splice(toIndex, 0, movedFile);

    renderMergeFileList();
}

function setSelectedFiles(files) {
    selectedFiles = Array.from(files);
    renderMergeFileList();
}

function setMergeButtonDisabled(disabled) {
    mergeButton.disabled = disabled;
}

function resetMergeResultArea() {
    mergeResultSection.style.display = "none";

    mergeStatusStep.textContent = "대기 중";
    mergeStatusMessage.textContent = "작업을 기다리고 있습니다.";
    mergeProgressBar.style.width = "0%";
    mergeProgressText.textContent = "0%";

    mergeDownloadTitle.style.display = "none";
    mergeDownloadList.innerHTML = "";

    mergeResetLink.style.display = "none";
    mergeResetLink.href = "/merge";
}

function showMergeStatus(step, message, progress) {
    mergeResultSection.style.display = "block";

    mergeStatusStep.textContent = step || "진행 중";
    mergeStatusMessage.textContent = message || "";

    const numericProgress = Number(progress || 0);
    const safeProgress = Math.max(0, Math.min(100, numericProgress));

    mergeProgressBar.style.width = `${safeProgress}%`;
    mergeProgressText.textContent = `${safeProgress}%`;
}

function showMergeDownload(job) {
    mergeDownloadList.innerHTML = "";

    if (job.merged_mp3_url) {
        const item = document.createElement("li");
        const link = document.createElement("a");

        link.href = job.merged_mp3_url;
        link.textContent = "병합된 MP3 다운로드";

        item.appendChild(link);
        mergeDownloadList.appendChild(item);

        mergeDownloadTitle.style.display = "block";
    }

    if (job.cleanup_url) {
        mergeResetLink.href = job.cleanup_url;
        mergeResetLink.style.display = "inline-block";
    }
}

async function pollMergeJob(jobId) {
    try {
        const response = await fetch(`/merge/jobs/${jobId}`, {
            cache: "no-store",
        });

        const job = await response.json();

        showMergeStatus(job.step, job.message, job.progress);
        showMergeDownload(job);

        if (job.status === "complete" || job.status === "failed") {
            if (mergePollingTimer) {
                clearInterval(mergePollingTimer);
                mergePollingTimer = null;
            }

            setMergeButtonDisabled(false);
            mergeButton.textContent = "이 순서대로 MP3 합치기";

            if (job.status === "failed") {
                showMergeStatus(
                    "오류 발생",
                    job.message || "병합 작업 중 오류가 발생했습니다.",
                    100
                );
            }
        }
    } catch (error) {
        if (mergePollingTimer) {
            clearInterval(mergePollingTimer);
            mergePollingTimer = null;
        }

        setMergeButtonDisabled(false);
        mergeButton.textContent = "이 순서대로 MP3 합치기";
        showMergeStatus("오류 발생", "병합 상태를 가져오지 못했습니다.", 100);
    }
}

async function startMergeJob() {
    if (selectedFiles.length === 0) {
        alert("먼저 파일을 선택해주세요.");
        return;
    }

    if (selectedFiles.length < 2) {
        alert("MP3 병합은 파일을 2개 이상 선택해야 합니다.");
        return;
    }

    if (mergePollingTimer) {
        clearInterval(mergePollingTimer);
        mergePollingTimer = null;
    }

    resetMergeResultArea();

    const formData = new FormData();

    selectedFiles.forEach((file) => {
        formData.append("files", file);
    });

    setMergeButtonDisabled(true);
    mergeButton.textContent = "병합 중입니다...";

    showMergeStatus("업로드 중", "파일들을 서버로 업로드하고 있습니다.", 5);

    try {
        const response = await fetch("/merge/jobs", {
            method: "POST",
            body: formData,
            cache: "no-store",
        });

        const data = await response.json();

        if (!response.ok) {
            setMergeButtonDisabled(false);
            mergeButton.textContent = "이 순서대로 MP3 합치기";
            showMergeStatus(
                "오류 발생",
                data.error || "병합 작업을 시작하지 못했습니다.",
                100
            );
            return;
        }

        mergePollingTimer = setInterval(() => {
            pollMergeJob(data.job_id);
        }, 500);

        pollMergeJob(data.job_id);
    } catch (error) {
        setMergeButtonDisabled(false);
        mergeButton.textContent = "이 순서대로 MP3 합치기";
        showMergeStatus("오류 발생", "서버 요청 중 오류가 발생했습니다.", 100);
    }
}

mergeFileInput.addEventListener("change", () => {
    setSelectedFiles(mergeFileInput.files);
});

mergeUploadBox.addEventListener("dragover", (event) => {
    event.preventDefault();
    mergeUploadBox.classList.add("drag-over");
});

mergeUploadBox.addEventListener("dragleave", () => {
    mergeUploadBox.classList.remove("drag-over");
});

mergeUploadBox.addEventListener("drop", (event) => {
    event.preventDefault();
    mergeUploadBox.classList.remove("drag-over");

    const droppedFiles = event.dataTransfer.files;

    if (!droppedFiles || droppedFiles.length === 0) {
        return;
    }

    setSelectedFiles(droppedFiles);
});

mergeButton.addEventListener("click", () => {
    startMergeJob();
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

    menuButton.addEventListener("click", openMenu);
    closeMenuButton.addEventListener("click", closeMenu);
    menuOverlay.addEventListener("click", closeMenu);
}

setupNavigationMenu();