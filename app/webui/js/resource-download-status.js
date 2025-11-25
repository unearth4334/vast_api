// Resource Download Status UI
// Polls /downloads/status and renders download queue/progress for the selected instance

export class ResourceDownloadStatus {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.instanceId = null;
        this.pollInterval = null;
    }

    setInstanceId(instanceId) {
        this.instanceId = instanceId;
        this.startPolling();
    }

    startPolling() {
        if (this.pollInterval) clearInterval(this.pollInterval);
        this.pollInterval = setInterval(() => this.pollStatus(), 2000);
        this.pollStatus();
    }

    async pollStatus() {
        if (!this.instanceId) return;
        try {
            const jobs = await window.api.get(`/downloads/status?instance_id=${this.instanceId}`);
            this.render(jobs);
        } catch (e) {
            this.container.innerHTML = '<div class="error">Failed to load download status</div>';
        }
    }

    render(jobs) {
        if (!jobs || jobs.length === 0) {
            this.container.innerHTML = '<div class="no-downloads">No downloads queued for this instance.</div>';
            return;
        }
        this.container.innerHTML = jobs.map(job => this.renderJob(job)).join('');
    }

    renderJob(job) {
        let progressBar = '';
        if (job.status === 'RUNNING' && job.progress && typeof job.progress.percent === 'number') {
            progressBar = `<div class="progress-bar"><div class="progress" style="width: ${job.progress.percent}%;"></div></div>`;
        }
        let statusText = job.status;
        if (job.status === 'RUNNING' && job.progress && job.progress.speed) {
            statusText += ` (${job.progress.percent || 0}% @ ${job.progress.speed})`;
        }
        if (job.status === 'FAILED' && job.error) {
            statusText += `: ${job.error}`;
        }
        return `
            <div class="download-job ${job.status.toLowerCase()}">
                <div class="job-header">
                    <span class="job-id">Job: ${job.id.slice(0,8)}</span>
                    <span class="job-status">${statusText}</span>
                </div>
                <div class="job-commands">
                    ${job.commands.map(cmd => `<code>${cmd}</code>`).join('<br>')}
                </div>
                ${progressBar}
            </div>
        `;
    }
}
