#include <stdint.h>
/* Original R3 duty offset in ticks, clipped to +/-2310. Each segment
 * maps the inverse transfer directly, with Q12 slope and rounded output. */
struct knot {int16_t delta,duty,slope;};
static const struct knot k[]={
 {0,5625,5803}, {-123,4875,24976}, {-564,3750,10449},
 {-1107,2625,8486}, {-1251,1875,21333}, {-2550,0,5912}
};
int bc203_map(int unused,int delta){
 (void)unused;
 if(delta<=-1553)return 1440;
 if(delta>=308)return 6060;
 const struct knot *p=k;
 while(delta<p->delta)++p;
 int w=p->duty+(((delta-p->delta)*p->slope+2048)>>12);
 if(w<1440)w=1440;if(w>6060)w=6060;
 return w;
}
