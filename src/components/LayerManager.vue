<template>
  <div 
    class="layer-manager-card" 
    :style="{ top: '80px', right: '20px' }"
    v-show="visible"
  >
    <div class="card-header">
      <span class="title">图层管理</span>
      <div class="header-actions">
        <el-button link size="small" @click="toggleCollapse">
            <el-icon><ArrowDown v-if="!collapsed" /><ArrowRight v-else /></el-icon>
        </el-button>
        <el-button link size="small" @click="$emit('close')">
            <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <div v-show="!collapsed" class="card-body">
      <!-- 搜索框 -->
      <el-input
        v-model="filterText"
        placeholder="搜索图层..."
        size="small"
        clearable
        class="filter-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <!-- 快捷操作 -->
      <div class="quick-actions">
        <el-button size="small" link @click="expandAll">全部展开</el-button>
        <el-button size="small" link @click="collapseAll">全部折叠</el-button>
        <el-divider direction="vertical" />
        <el-button size="small" link @click="checkAll">全选</el-button>
        <el-button size="small" link @click="uncheckAll">全不选</el-button>
      </div>

      <!-- 图层树 -->
      <el-tree
        ref="treeRef"
        :data="treeData"
        show-checkbox
        node-key="id"
        default-expand-all
        :filter-node-method="filterNode"
        @check="handleCheckChange"
        :props="defaultProps"
      >
        <template #default="{ node, data }">
          <div class="custom-tree-node">
            <span>{{ node.label }}</span>
            <!-- 如果是叶子节点，显示透明度滑块 -->
            <div v-if="data.isLayer" class="node-actions" @click.stop>
                <el-popover placement="left" :width="200" trigger="hover">
                    <template #reference>
                        <el-icon class="setting-icon"><Setting /></el-icon>
                    </template>
                    <div class="opacity-control">
                        <span>透明度: {{ data.opacity }}%</span>
                        <el-slider 
                            v-model="data.opacity" 
                            :min="0" 
                            :max="100" 
                            size="small"
                            @input="(val: any) => handleOpacityChange(data.key, val)"
                        />
                    </div>
                </el-popover>
            </div>
          </div>
        </template>
      </el-tree>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Search, Close, ArrowDown, ArrowRight, Setting } from '@element-plus/icons-vue';
import { ElTree } from 'element-plus';

const props = defineProps<{
  visible: boolean;
  layerConfig: Record<string, any>;
}>();

const emit = defineEmits(['close', 'update:visibility', 'update:opacity']);

const collapsed = ref(false);
const filterText = ref('');
const treeRef = ref<InstanceType<typeof ElTree>>();

// 构建树形数据
// 根节点：图层管理
// 子节点：从 layerConfig 映射
const buildTreeData = () => {
  return [
    {
      id: 'root',
      label: '图层管理',
      children: Object.entries(props.layerConfig).map(([key, config]) => ({
        id: key,
        key: key,
        label: config.name,
        isLayer: true,
        opacity: config.opacity,
        // 如果 layerConfig 变化，这里可能需要响应式更新，但在 setup 中只运行一次
        // 所以我们最好使用 computed 或 watch 来同步
      }))
    }
  ];
};

// 这里的 treeData 需要是响应式的，并且双向绑定到 selection
const treeData = ref(buildTreeData());

// 监听 layerConfig 变化以更新树状态（如果外部修改了配置）
watch(() => props.layerConfig, (newConfig) => {
    // 简单处理：更新 opacity
    const root = treeData.value[0];
    if (root.children) {
        root.children.forEach((child: any) => {
            if (newConfig[child.key]) {
                child.opacity = newConfig[child.key].opacity;
            }
        });
    }
    // 更新勾选状态
    const checkedKeys = Object.entries(newConfig)
        .filter(([_, conf]) => conf.visible)
        .map(([key, _]) => key);
    
    // 加上 root 如果所有子节点都选中（这里简化处理，只设置叶子节点）
    treeRef.value?.setCheckedKeys(checkedKeys);
}, { deep: true, immediate: true });

const defaultProps = {
  children: 'children',
  label: 'label',
};

// 过滤
watch(filterText, (val) => {
  treeRef.value!.filter(val);
});

const filterNode = (value: string, data: any) => {
  if (!value) return true;
  return data.label.includes(value);
};

// 展开/折叠
const toggleCollapse = () => {
  collapsed.value = !collapsed.value;
};

const expandAll = () => {
    // ElTree 没有直接的 expandAll API，需要遍历 nodes
    // 这里简单处理：展开根节点即可，因为只有两层
    const nodes = treeRef.value!.store.nodesMap;
    for (const key in nodes) {
        nodes[key].expanded = true;
    }
};

const collapseAll = () => {
    const nodes = treeRef.value!.store.nodesMap;
    for (const key in nodes) {
        nodes[key].expanded = false;
    }
};

// 全选/全不选
const checkAll = () => {
    treeRef.value!.setCheckedKeys(['root']); // 选中根节点会自动选中所有子节点
    handleCheckChange();
};

const uncheckAll = () => {
    treeRef.value!.setCheckedKeys([]);
    handleCheckChange();
};

// 处理勾选变化
const handleCheckChange = () => {
    // 获取所有选中的叶子节点 key
    const checkedKeys = treeRef.value!.getCheckedKeys(true); // leafOnly = true
    
    // 遍历所有 layerConfig，更新 visible
    Object.keys(props.layerConfig).forEach(key => {
        const isVisible = checkedKeys.includes(key);
        emit('update:visibility', { key, visible: isVisible });
    });
};

// 处理透明度变化
const handleOpacityChange = (key: string, val: number) => {
    // 这里 val 是 slider 的值 (0-100) (element-plus slider v-model is number)
    // 但是类型定义可能是 Array | number，我们强制转为 number
    const opacity = Array.isArray(val) ? val[0] : val;
    emit('update:opacity', { key, opacity });
};

</script>

<style scoped>
.layer-manager-card {
  position: absolute;
  width: 300px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: height 0.3s;
}

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(245, 247, 250, 0.8);
  cursor: move; /* Indicate draggable if we implemented drag */
}

.title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.card-body {
  padding: 12px;
}

.filter-input {
  margin-bottom: 10px;
}

.quick-actions {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #eee;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding-right: 8px;
}

.setting-icon {
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}

.setting-icon:hover {
  color: #409eff;
}

.opacity-control {
    padding: 10px;
}
</style>
