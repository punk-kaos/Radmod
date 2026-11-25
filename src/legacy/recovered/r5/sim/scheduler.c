/* Synthetic RT950 timebase for the actual BTF machine code in Unicorn.
   Sample- and half-transfer events have separate phases. DMA57 can interrupt
   TIM6 at translated block boundaries. Peripheral addresses follow V317.
   The instruction/memory charges below are scenario parameters, not a model
   of the AT32 flash controller. */
#include <unicorn/unicorn.h>
#include <unicorn/arm.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define PERIOD 15000u
#define STOP 0x20000100u
#define STATE 0x20016000u
#define DMA 0x40020400u
#define TIM6 0x40001000u
#define FLASH 0x08000000u
#define RAM 0x20000000u
#define MEMIO 0x40000000u
#define REG70_RING 0x20016128u

typedef struct {
    uint32_t target, phase, flash_cost, dma_floor, launch_tick, ram_exec, flash_data, ram_data;
} Config;
typedef struct {
    uint32_t frames, ticks, coalesced, preemptions, holds, running, fault, last_writer;
    uint32_t peak_ops, peak_work, peak_elapsed, peak_dma, max_entry_lag;
    uint32_t tim7_ticks, release, release_command, stack_ok;
    uint64_t ops, own_work, isrs;
} Result;
typedef struct {
    uc_engine *uc;
    uc_context *saved;
    Config c;
    Result *r;
    const uint16_t *adc;
    unsigned n_adc;
    uint8_t *trace;
    uint64_t now, next6, next57, spent, tim6_enter;
    uint32_t flags6, flags57, half, ops6;
    int irq;
    bool pending6, timed, preempt, nested;
} Clock;

static uint32_t read32(uc_engine *uc, uint32_t addr) {
    uint32_t v=0; uc_mem_read(uc,addr,&v,4); return v;
}
static uint8_t read8(uc_engine *uc, uint32_t addr) {
    uint8_t v=0; uc_mem_read(uc,addr,&v,1); return v;
}
static void write32(uc_engine *uc, uint32_t addr, uint32_t v) {
    uc_mem_write(uc,addr,&v,4);
}
static uint32_t cpu(uc_engine *uc, int reg) {
    uint32_t v=0; uc_reg_read(uc,reg,&v); return v;
}
static void update_peak(uint32_t *peak, uint32_t v) { if(v>*peak)*peak=v; }

static void events(Clock *m) {
    while (m->next6<=m->now) {
        if (m->pending6) m->r->coalesced++;
        unsigned index=m->r->ticks++;
        write32(m->uc,0x40013c4cu,m->adc[index % m->n_adc]);
        m->flags6=1; m->pending6=true; m->next6+=PERIOD;
    }
    while (m->next57<=m->now) {
        m->flags57 |= m->half ? 32 : 64;
        m->half ^= 1; m->next57+=PERIOD;
    }
}
static void advance(Clock *m, uint32_t amount) {
    m->now+=amount;
    if (m->irq==6) m->spent+=amount;
}
static void code(uc_engine *uc, uint64_t pc, uint32_t size, void *data) {
    (void)size;
    Clock *m=data;
    if (pc==RAM) {
        if (cpu(uc,UC_ARM_REG_R0)==0x30)
            m->r->last_writer=cpu(uc,UC_ARM_REG_R1);
    }
    if (!m->timed) return;
    if (m->irq==6) {
        m->ops6++;
    }
    /* The previous image moved its gradient kernel into trace SRAM. Sweep
       that fetch cost independently of the already proven transport in SRAM. */
    bool voice_sram=pc>=0x20017a94u && pc<0x20017d94u;
    advance(m,pc<RAM ? m->c.flash_cost : voice_sram ? m->c.ram_exec : 1);
    /* Charge the chosen measured DMA render interval INSIDE the two DWT
       reads. IRQ entry, shutdown and the rest of the handler are additional. */
    if (m->irq==57 && pc==0x0806329cu) {
        uint32_t start=cpu(uc,UC_ARM_REG_R9);
        uint32_t elapsed=(uint32_t)m->now-start+3u;
        if (elapsed<m->c.dma_floor) advance(m,m->c.dma_floor-elapsed);
    }
}
/* Memory callbacks are made for each constituent word of an LDM/STM. */
static void memory(uc_engine *uc, uc_mem_type type, uint64_t addr, int size,
                   int64_t value, void *data) {
    (void)size;
    Clock *m=data;
    if (!m->timed) return;
    advance(m, addr < RAM ? m->c.flash_data : addr < MEMIO ? m->c.ram_data : 3);
    if (addr < MEMIO) return;
    events(m);
    if (type==UC_MEM_READ) {
        if (addr==0xe0001004u) write32(uc,addr,(uint32_t)m->now);
        else if (addr==TIM6+0x24) write32(uc,addr,(m->now%PERIOD)/60);
        else if (addr==TIM6+0x10) write32(uc,addr,m->flags6);
        else if (addr==DMA) write32(uc,addr,m->flags57);
        else if (addr==0xe000e304u) write32(uc,addr,m->nested ? (1u<<22) : 0);
        else if (addr==DMA+0x20) {
            uint32_t since=(uint32_t)((m->now+2*PERIOD-m->c.phase)%(2*PERIOD));
            uint32_t count=since<PERIOD ? 625u-since/24u : 1250u-(since-PERIOD)/24u;
            write32(uc,addr,count);
        }
    } else if (addr==TIM6+0x10 && !(value&1u)) m->flags6=0;
    else if (addr==DMA+4) m->flags57 &= ~(uint32_t)value;
}
static void block(uc_engine *uc, uint64_t addr, uint32_t size, void *data) {
    (void)addr; (void)size;
    Clock *m=data;
    if (!m->timed) return;
    events(m);
    if (m->irq==6 && m->flags57) {
        m->preempt=true;
        uc_emu_stop(uc);
    }
}

static int enter(Clock *m, uint32_t pc, uint32_t arg) {
    uint32_t lr=STOP|1;
    uc_reg_write(m->uc,UC_ARM_REG_LR,&lr);
    uc_reg_write(m->uc,UC_ARM_REG_R0,&arg);
    return uc_emu_start(m->uc,pc|1,STOP,0,0);
}
static uint8_t serialized_gain(uc_engine *uc,unsigned half) {
    uint32_t words[49];
    uc_mem_read(uc,REG70_RING+(half*625+3)*4,words,sizeof(words));
    uint8_t gain=0;
    for (unsigned b=0;b<7;b++) gain |= ((words[46-2*b]>>11)&1u)<<b;
    return gain;
}
static int dma(Clock *m,uint32_t vector) {
    uint32_t before=read32(m->uc,STATE+4);
    uint64_t entry=m->now;
    m->irq=57;
    int ret=enter(m,vector,0);
    if (ret) return ret;
    uint32_t elapsed=(uint32_t)(m->now-entry);
    update_peak(&m->r->peak_dma,elapsed);
    events(m);
    uint32_t after=read32(m->uc,STATE+4);
    if (after==before+1 && before<m->c.target && read8(m->uc,STATE+0x81)) {
        m->trace[before]=serialized_gain(m->uc,before&1u);
    }
    return 0;
}

int run_clock(uc_engine *uc,Config *config,const uint16_t *adc,unsigned length,
              uint8_t *trace,Result *result) {
    Clock m={.uc=uc,.c=*config,.r=result,.adc=adc,.n_adc=length,.trace=trace};
    memset(result,0,sizeof(*result));
    uc_hook h[3]; int err=0;
    if ((err=uc_context_alloc(uc,&m.saved))) return err;
    if ((err=uc_hook_add(uc,&h[0],UC_HOOK_CODE,code,&m,1,0))) goto done;
    if ((err=uc_hook_add(uc,&h[1],UC_HOOK_BLOCK,block,&m,1,0))) goto hook1;
    if ((err=uc_hook_add(uc,&h[2],UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,memory,&m,1,0))) goto hook2;
    uint32_t t6=read32(uc,0x08003118u), irq57=read32(uc,0x08003124u);
    uint32_t initial_sp=cpu(uc,UC_ARM_REG_SP);
    /* The Python driver has already exercised TIM7 from tick zero through launch. */
    if (!read8(uc,STATE+0x81)) { err=-1; goto cleanup; }
    uint64_t next7=57300u; /* 60 x 955 MCU clocks per TIM7 tick. */
    m.timed=true; m.next57=config->phase;
    while ((result->frames=read32(uc,STATE+4))<config->target && read8(uc,STATE+0x81)) {
        events(&m);
        if (m.flags57) {
            if ((err=dma(&m,irq57))) goto cleanup;
        } else if (m.pending6) {
            m.pending6=false; m.irq=6; m.ops6=0; m.spent=0; m.tim6_enter=m.now;
            update_peak(&result->max_entry_lag,(uint32_t)(m.now%PERIOD));
            m.preempt=false;
            err=enter(&m,t6,0);
            while (!err && m.preempt) {
                m.preempt=false; m.nested=true;
                result->preemptions++;
                if ((err=uc_context_save(uc,m.saved))) break;
                uint32_t sp=cpu(uc,UC_ARM_REG_SP)-32u;
                uc_reg_write(uc,UC_ARM_REG_SP,&sp);
                // Hardware saves the interrupted xPSR and clears ITSTATE on
                // exception entry. The IRQ must not inherit a Thumb IT block.
                uint32_t psr=cpu(uc,UC_ARM_REG_XPSR)&~0x0600fc00u;
                uc_reg_write(uc,UC_ARM_REG_XPSR,&psr);
                if ((err=dma(&m,irq57))) break;
                if ((err=uc_context_restore(uc,m.saved))) break;
                m.nested=false; m.irq=6;
                err=uc_emu_start(uc,cpu(uc,UC_ARM_REG_PC)|1,STOP,0,0);
            }
            if (err) goto cleanup;
            update_peak(&result->peak_ops,m.ops6);
            update_peak(&result->peak_work,(uint32_t)m.spent);
            update_peak(&result->peak_elapsed,(uint32_t)(m.now-m.tim6_enter));
            result->ops+=m.ops6; result->own_work+=m.spent; result->isrs++;
        } else if (m.now>=next7) {
            /* Dispatch one FIFO/UART service call at an idle CPU boundary.
               Charge its execution atomically at this lower priority. */
            m.irq=7;
            uint32_t tick=config->launch_tick+(++result->tim7_ticks);
            if ((err=enter(&m,0x08047e38u,tick))) goto cleanup;
            next7+=57300u;
        } else {
            m.now=m.next6<m.next57 ? m.next6 : m.next57;
            if (next7<m.now) m.now=next7;
        }
        m.irq=0;
    }
    result->frames=read32(uc,STATE+4);
    result->holds=read32(uc,STATE+0x60);
    result->fault=read32(uc,0x20017e74u);
    result->running=read8(uc,STATE+0x81);
    if (result->running) {
        /* Unkey at the next real DMA event. */
        uint32_t ticks=result->ticks, dropped=result->coalesced, peak=result->peak_dma;
        write32(uc,0x40011808u,0x2cu); m.now=m.next57; events(&m);
        if ((err=dma(&m,irq57))) goto cleanup;
        result->ticks=ticks; result->coalesced=dropped; result->peak_dma=peak;
    }
    result->release=read32(uc,0x20017e74u);
    result->release_command=result->last_writer;
    result->stack_ok=cpu(uc,UC_ARM_REG_SP)==initial_sp;
cleanup:
    uc_hook_del(uc,h[2]);
hook2: uc_hook_del(uc,h[1]);
hook1: uc_hook_del(uc,h[0]);
done: uc_context_free(m.saved);
    return err;
}
