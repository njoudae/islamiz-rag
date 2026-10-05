<script setup>
import { LOGO } from '../lib/icons.js';
</script>

<template>
    <!-- The design's mark. display:contents keeps the SVG laid out as a direct child, as in the design. -->
    <span style="display: contents" v-html="LOGO" />
</template>
