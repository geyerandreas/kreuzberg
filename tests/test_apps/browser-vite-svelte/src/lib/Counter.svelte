<script lang="ts">
let _count: number = $state(0);
const _increment = () => {
	_count += 1;
};
</script>

<button onclick={increment}>
  count is {count}
</button>
