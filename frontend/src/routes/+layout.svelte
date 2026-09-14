<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Go2 智能巡检系统</title>
</svelte:head>

<div class="app-shell">
	<div class="bg-grid" aria-hidden="true"></div>
	<div class="bg-orb bg-orb-1" aria-hidden="true"></div>
	<div class="bg-orb bg-orb-2" aria-hidden="true"></div>
	<div class="bg-orb bg-orb-3" aria-hidden="true"></div>

	<div class="relative z-10">
		{@render children()}
	</div>
</div>

<style>
	.app-shell {
		position: relative;
		min-height: 100vh;
		overflow-x: hidden;
	}

	.bg-grid {
		position: fixed;
		inset: 0;
		pointer-events: none;
		background-image:
			linear-gradient(rgba(148, 163, 184, 0.05) 1px, transparent 1px),
			linear-gradient(90deg, rgba(148, 163, 184, 0.05) 1px, transparent 1px);
		background-size: 44px 44px;
		mask-image: radial-gradient(ellipse at center, black 35%, transparent 80%);
		-webkit-mask-image: radial-gradient(ellipse at center, black 35%, transparent 80%);
		z-index: 0;
	}

	.bg-orb {
		position: fixed;
		border-radius: 999px;
		filter: blur(120px);
		pointer-events: none;
		opacity: 0.32;
		z-index: 0;
	}
	.bg-orb-1 {
		width: 520px; height: 520px;
		background: #22d3ee;
		top: -200px; left: -140px;
		animation: drift1 14s ease-in-out infinite;
	}
	.bg-orb-2 {
		width: 420px; height: 420px;
		background: #a78bfa;
		top: 38%; right: -160px;
		animation: drift2 16s ease-in-out infinite;
	}
	.bg-orb-3 {
		width: 380px; height: 380px;
		background: #3b82f6;
		bottom: -180px; left: 32%;
		animation: drift3 18s ease-in-out infinite;
	}

	@keyframes drift1 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		50%      { transform: translate(48px, 64px) scale(1.08); }
	}
	@keyframes drift2 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		50%      { transform: translate(-64px, -40px) scale(1.1); }
	}
	@keyframes drift3 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		50%      { transform: translate(-36px, 28px) scale(0.94); }
	}
</style>